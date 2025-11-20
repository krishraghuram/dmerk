import logging
from typing import Any, Callable, cast, Optional
from enum import Enum
from dataclasses import dataclass

from textual.widget import Widget
from textual.widgets import TabbedContent, DataTable
from textual.widgets._tabbed_content import ContentTab, ContentTabs
from textual.app import App
from textual.events import Key, DescendantFocus, Focus, DescendantBlur, Blur


class Direction(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"

    @classmethod
    def from_key(cls, key: str) -> "Direction":
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


class NavigationSchema:
    def __init__(self, app: App):
        from dmerk.tui.app import Tabs

        self.app = app

        self._schema: NavSchema = {
            "TabbedContent": {
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
                Direction.RIGHT: (None, True),
                Direction.LEFT: (None, True),
            },
            "FavoritesSidebar": {
                # Direction.UP: RelativeTarget.FOCUS_PREVIOUS,
                # Direction.DOWN: RelativeTarget.FOCUS_NEXT,
                Direction.RIGHT: "FileManager",
            },
            "SidebarButton": {
                Direction.UP: lambda w, d: (
                    "ContentTabs" if w.first_child else RelativeTarget.FOCUS_PREVIOUS
                ),
                Direction.DOWN: lambda w, d: (
                    "RichLog" if w.last_child else RelativeTarget.FOCUS_NEXT
                ),
            },
            "FileManager ClearableInput": {
                Direction.UP: "ContentTabs",
                Direction.DOWN: "FileManager DataTable",
                Direction.LEFT: "FavoritesSidebar",
            },
            "FileManager DataTable": {
                Direction.UP: lambda w, d: (
                    (
                        "FileManager ClearableInput"
                        if cast(DataTable, w).cursor_row == 0
                        else None
                    ),
                    True,
                ),
                Direction.DOWN: (None, True),
                Direction.LEFT: lambda w, d: (
                    (
                        "FavoritesSidebar"
                        if cast(DataTable, w).cursor_column == 0
                        else None
                    ),
                    True,
                ),
                Direction.RIGHT: (None, True),
            },
        }

        # # Tabs
        # def tab_down(w: Widget, d: Direction):

        #     w = cast(TabbedContent, w)
        #     if w.active == Tabs.Generate.value:
        #         w.query_one("FavoritesSidebar SidebarButton").focus()
        #     elif w.active == Tabs.Compare.value:
        #         w.query_one("ClearableInput Input").focus()

        # self._schema.update({"TabbedContent": {Direction.DOWN: tab_down}})

        # # SidebarButton
        # def up(w: Widget, d: Direction):
        #     if not w.first_child:
        #         w.screen.focus_previous()
        #     elif w.first_child:
        #         w.app.query_one(ContentTabs).focus()

        # def down(w: Widget, d: Direction):
        #     if not w.last_child:
        #         w.screen.focus_next()

        # self._schema.update(
        #     {
        #         w: {
        #             Direction.UP: up,
        #             Direction.DOWN: down,
        #             Direction.RIGHT: "FileManager ClearableInput Input",
        #         }
        #         for w in self.app.query("SidebarButton")
        #     }
        # )

        # # FileManager
        # def filemanager(w: Widget, d: Direction):
        #     match d:
        #         case Direction.LEFT:
        #             if cast(FileManager, w).query_one(DataTable).cursor_column == 0:
        #                 w.app.query("FavoritesSidebar").focus()
        #         case Direction.UP:
        #             if cast(FileManager, w).query_one(DataTable).cursor_row == 0:
        #                 w.app.query("ClearableInput").focus()

        # self._schema.update(
        #     {
        #         "FileManager": {
        #             Direction.LEFT: filemanager,
        #             Direction.UP: "ContentTabs",
        #         }
        #     }
        # )

    def navigate(self, widget: Widget, direction: Direction) -> Bubble:
        for nav_source, nav_targets in self._schema.items():
            if isinstance(nav_source, DomQuery):
                nav_sources = list(self.app.query(nav_source))
            else:
                nav_sources = [nav_source]
            for nav_source in nav_sources:
                if nav_source == widget:
                    nav_target = nav_targets.get(direction)
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
    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, Widget)
        super().__init__(*args, **kwargs)

    def on_key(self, event: Key) -> None:
        assert isinstance(self, Widget)
        from dmerk.tui.app import DmerkApp

        try:
            direction = Direction.from_key(event.key)
        except ValueError:
            return
        if not cast(DmerkApp, self.app).navigation_schema.navigate(self, direction):
            event.stop()


class FocusPassthroughMixin:
    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, Widget)
        super().__init__(*args, **kwargs)
        self._child_to_passthrough_focus: Widget | None = None
        self._previously_focused: Widget | None = None
        self.can_focus: bool = True

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        assert isinstance(self, Widget)
        self._child_to_passthrough_focus = event.widget
        self._previously_focused = self.app.focused

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        assert isinstance(self, Widget)
        self._previously_focused = self.app.focused

    def descendant_had_focus(self) -> bool:
        "Return true if previously focused widget was a child"
        return bool(
            self._previously_focused
            and self in self._previously_focused.ancestors_with_self
        )

    def on_focus(self, event: Focus) -> None:
        assert isinstance(self, Widget)
        # If focus came from one of our descendants, don't trap it
        if self.descendant_had_focus():
            self.app.screen.focus_previous()
        else:
            # Focus came from outside - pass through to child
            if self._child_to_passthrough_focus:
                self._child_to_passthrough_focus.focus()
            else:
                self.app.screen.focus_next()

    def on_blur(self, event: Blur) -> None:
        assert isinstance(self, Widget)
        self._previously_focused = self.app.focused


# Patch mixins into textual widgets
navigation_mixin_classes = [
    TabbedContent,
    DataTable,
]
for cls in navigation_mixin_classes:
    cls.__bases__ = cls.__bases__ + (NavigationMixin,)
focus_passthrough_mixin_classes = [TabbedContent]
for cls in focus_passthrough_mixin_classes:
    cls.__bases__ = cls.__bases__ + (FocusPassthroughMixin,)
