import logging
from typing import Any, Callable, cast, Optional
from enum import Enum
from dataclasses import dataclass
import functools
from collections import defaultdict

from textual.css.query import NoMatches
from textual.dom import DOMNode
from textual.widget import Widget
from textual.widgets import TabbedContent, DataTable, RichLog, Button
from textual.widgets._tabbed_content import ContentTab, ContentTabs
from textual.app import App
from textual.events import Key, DescendantFocus, Focus, DescendantBlur, Blur
from textual.containers import Horizontal, Vertical


class Direction(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"

    @classmethod
    def from_key(cls, key: str | None) -> "Direction":
        if key == "up":
            return cls.UP
        elif key == "down":
            return cls.DOWN
        elif key == "left":
            return cls.LEFT
        elif key == "right":
            return cls.RIGHT
        else:
            raise ValueError(f"Unexpected value {key=} in Direction.from_key")


class RelativeTarget(Enum):
    FOCUS_PREVIOUS = "FocusPrevious"
    FOCUS_NEXT = "FocusNext"


Bubble = bool
DomQuery = str
Source = DomQuery | Widget
AbsoluteTarget = DomQuery | Widget
StaticTarget = (
    AbsoluteTarget
    | RelativeTarget
    | None
    | tuple[AbsoluteTarget | RelativeTarget | None, Bubble]
)
CallableTarget = Callable[[Widget, Direction], StaticTarget]
Target = StaticTarget | CallableTarget
NavSchema = dict[Source, dict[Direction, Target]]

# defaultdict used in NavSchema, that returns (None,True)
# None, meaning we dont want to focus any widget
# True, meaning we want to bubble the event
dd: Callable = functools.partial(defaultdict, lambda: (None, True))


class NavigationSchema:
    def __init__(self, app: App):
        from dmerk.tui.app import Tabs, DmerkApp

        self.app = app

        self._schema: NavSchema = {
            "TabbedContent": dd(
                {
                    Direction.UP: (None, True),
                    Direction.DOWN: lambda w, d: (
                        (
                            (
                                "ClearableInput"
                                if cast(TabbedContent, w).active == Tabs.Compare.value
                                else "FavoritesSidebar"
                            )
                            if isinstance(w.app.focused, ContentTabs)
                            else None
                        ),
                        True,
                    ),
                }
            ),
            "FavoritesSidebar": dd(
                {
                    Direction.RIGHT: "FileManager",
                }
            ),
            "SidebarButton": dd(
                {
                    Direction.UP: lambda w, d: (
                        "ContentTabs"
                        if w.first_child
                        else RelativeTarget.FOCUS_PREVIOUS
                    ),
                    Direction.DOWN: lambda w, d: (
                        "TabPane#tab-generate Vertical Horizontal#bottom"
                        if w.last_child
                        else RelativeTarget.FOCUS_NEXT
                    ),
                }
            ),
            "FileManager ClearableInput": dd(
                {
                    Direction.UP: "ContentTabs",
                    Direction.DOWN: "FileManager DataTable",
                    Direction.LEFT: "FavoritesSidebar",
                }
            ),
            "FileManager DataTable": dd(
                {
                    # TODO: Unlike <dir>, alt+<dir> should work even when not on row=0 or column=0
                    Direction.UP: lambda w, d: (
                        (
                            "FileManager ClearableInput"
                            if cast(DataTable, w).cursor_row == 0
                            else None
                        ),
                        True,
                    ),
                    Direction.LEFT: lambda w, d: (
                        (
                            "FavoritesSidebar"
                            if cast(DataTable, w).cursor_column == 0
                            else None
                        ),
                        True,
                    ),
                    # Direction.DOWN: "TabPane#tab-generate Vertical Horizontal#bottom",
                    Direction.DOWN: lambda w, d: (
                        (
                            ("TabPane#tab-generate Vertical Horizontal#bottom", False)
                            if cast(DataTable, w).cursor_row
                            == cast(DataTable, w).row_count - 1
                            else (None, True)
                        )
                    ),
                }
            ),
            "RichLog": dd(
                {
                    Direction.UP: lambda w, d: (
                        ("TabPane#tab-generate Vertical Horizontal#top", False)
                        if cast(RichLog, w).scroll_y == 0
                        else (None, True)
                    ),
                    Direction.RIGHT: f"Button#{cast(DmerkApp, self.app).BUTTON_GENERATE}",
                }
            ),
            f"Button#{cast(DmerkApp, self.app).BUTTON_GENERATE}": dd(
                {
                    Direction.UP: "TabPane#tab-generate Vertical Horizontal#top",
                    Direction.LEFT: "RichLog",
                }
            ),
        }

    def navigate(self, widget: Widget, direction: Direction) -> Bubble:
        for nav_source, nav_targets in self._schema.items():
            if isinstance(nav_source, DomQuery):
                nav_sources = list(self.app.query(nav_source))
            else:
                nav_sources = [nav_source]
            for nav_source in nav_sources:
                if nav_source == widget:
                    nav_target = nav_targets[direction]
                    bubble = False
                    if callable(nav_target):
                        nav_target = nav_target(nav_source, direction)
                    if isinstance(nav_target, tuple):
                        nav_target, bubble = nav_target
                    if isinstance(nav_target, DomQuery):
                        nav_target = self.app.query_one(nav_target)
                    if nav_target is not None:
                        if nav_target == RelativeTarget.FOCUS_NEXT:
                            self.app.screen.focus_next()
                        elif nav_target == RelativeTarget.FOCUS_PREVIOUS:
                            self.app.screen.focus_previous()
                        else:
                            nav_target.focus()
                    logging.debug(
                        f"In NavigationSchema.navigate, {nav_source=}, {direction=}, {nav_target=}, {bubble=}"
                    )
                    return bubble
        return True


class NavigationMixin:
    KEY_TAB = "tab"
    KEY_SHIFT = "shift"
    COMBINER = "+"
    MODIFIER = KEY_SHIFT
    DIRECTIONS = ["up", "down", "left", "right"]

    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, Widget)
        super().__init__(*args, **kwargs)

    def _get_direction(self, event_key: str) -> str | None:
        keys = event_key.split(self.COMBINER)
        if len(keys) == 1 and keys[0] in self.DIRECTIONS:
            return keys[0]
        # elif len(keys) == 2 and self.MODIFIER in keys:
        #     return list(set(keys) - {self.MODIFIER})[0]
        return None

    def on_key(self, event: Key) -> None:
        assert isinstance(self, Widget)
        from dmerk.tui.app import DmerkApp

        try:
            direction_str = self._get_direction(event.key)
            direction = Direction.from_key(direction_str)
        except ValueError:
            return
        if not cast(DmerkApp, self.app).navigation_schema.navigate(self, direction):
            event.stop()


class FocusDirection(Enum):
    """
    Indicate the direction in which user is moving focus.
    """

    NEXT = "next"
    PREVIOUS = "previous"


class FocusPassthroughMixin:
    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, DOMNode)
        super().__init__(*args, **kwargs)
        self._child_to_passthrough_focus: Widget | None = None
        self._previously_focused: Widget | None = None
        self.can_focus: bool = True

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        assert isinstance(self, DOMNode)
        self._child_to_passthrough_focus = event.widget
        self._previously_focused = self.app.focused

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        assert isinstance(self, DOMNode)
        self._previously_focused = self.app.focused

    def _descendant_had_focus(self) -> bool:
        "Return true if previously focused widget was a child"
        return bool(
            self._previously_focused
            and self in self._previously_focused.ancestors_with_self
        )

    def _focus_direction(self) -> FocusDirection:
        assert isinstance(self, Widget)
        assert isinstance(self.app, FocusPassthroughMixin)
        DEFAULT = FocusDirection.NEXT
        app_previously_focused = self.app._previously_focused
        if app_previously_focused is None:
            return DEFAULT

        focus_chain = self.screen.focus_chain
        try:
            prev_idx = focus_chain.index(app_previously_focused)
            curr_idx = focus_chain.index(self)
            # logging.debug(f"{prev_idx=}, {curr_idx=}, {len(focus_chain)=}")
            if curr_idx == 0 and prev_idx == len(focus_chain) - 1:
                focus_direction = FocusDirection.NEXT
            elif prev_idx < curr_idx:
                focus_direction = FocusDirection.NEXT
            elif prev_idx > curr_idx:
                focus_direction = FocusDirection.PREVIOUS
            else:
                raise ValueError(
                    "prev_idx == curr_idx in FocusPassthroughMixin.focus_direction"
                )
            logging.debug(f"{focus_direction=}")
            return focus_direction
        except ValueError:
            return DEFAULT

    def _on_content_tabs_descendant_focus(self) -> bool:
        assert isinstance(self, Widget)
        assert isinstance(self.app, FocusPassthroughMixin)
        app_previously_focused = self.app._previously_focused
        try:
            content_tabs = self.app.query_one(ContentTabs)
            if (
                app_previously_focused
                and content_tabs not in app_previously_focused.ancestors_with_self
                and content_tabs in self.ancestors_with_self
            ):
                return True
        except NoMatches as e:
            pass
        return False

    def on_focus(self, event: Focus) -> None:
        assert isinstance(self, DOMNode)
        # Special Cases
        if isinstance(self, TabbedContent):
            for node in self.app.walk_children():
                if isinstance(node, FocusPassthroughMixin):
                    node._child_to_passthrough_focus = None
        # If focus came from one of our descendants, don't trap it
        if self._descendant_had_focus():
            match self._focus_direction():
                case FocusDirection.PREVIOUS:
                    self.app.screen.focus_previous()
                case FocusDirection.NEXT:
                    self.app.screen.focus_next()
        else:
            # Focus came from outside - pass through to child
            if self._child_to_passthrough_focus:
                self._child_to_passthrough_focus.focus()
            else:
                match self._focus_direction():
                    case FocusDirection.PREVIOUS:
                        self.app.screen.focus_previous()
                    case FocusDirection.NEXT:
                        self.app.screen.focus_next()

    def on_blur(self, event: Blur) -> None:
        assert isinstance(self, Widget)
        self._previously_focused = self.app.focused


# Patch textual widgets
set_can_focus_classes = [Horizontal, Vertical]
for cls in set_can_focus_classes:
    cls.can_focus = True
navigation_mixin_classes: list[type[Widget]] = [
    TabbedContent,
    DataTable,
    RichLog,
    Horizontal,
    Vertical,
    Button,
]
for cls in navigation_mixin_classes:
    cls.__bases__ = (NavigationMixin,) + cls.__bases__
focus_passthrough_mixin_classes: list[type[Widget]] = [
    TabbedContent,
    Horizontal,
    Vertical,
]
for cls in focus_passthrough_mixin_classes:
    cls.__bases__ = (FocusPassthroughMixin,) + cls.__bases__
