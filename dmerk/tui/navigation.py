import logging
from dataclasses import dataclass
from enum import Enum
from functools import singledispatchmethod
from typing import Any, cast

from textual.app import App
from textual.css.query import NoMatches
from textual.events import Key as TextualKeyEvent
from textual.geometry import Offset, Region, Size
from textual.widget import Widget
from textual.widgets import DataTable, Input
from textual.widgets._tabbed_content import ContentTab, ContentTabs


class Key(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"
    CTRL_UP = "CtrlUp"
    CTRL_DOWN = "CtrlDown"
    CTRL_LEFT = "CtrlLeft"
    CTRL_RIGHT = "CtrlRight"

    @classmethod
    def from_event(cls, event: TextualKeyEvent) -> "Key":
        key = event.key
        match key:
            case "ctrl+up":
                return cls.CTRL_UP
            case "ctrl+down":
                return cls.CTRL_DOWN
            case "ctrl+left":
                return cls.CTRL_LEFT
            case "ctrl+right":
                return cls.CTRL_RIGHT
            case "up":
                return cls.UP
            case "down":
                return cls.DOWN
            case "left":
                return cls.LEFT
            case "right":
                return cls.RIGHT
            case _:
                raise ValueError(f"Unexpected value {key=} in Key.from_event")

    def has_ctrl(self):
        cls = self.__class__
        ctrl_keys = (cls.CTRL_UP, cls.CTRL_DOWN, cls.CTRL_LEFT, cls.CTRL_RIGHT)
        return self in ctrl_keys


class Direction(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"

    @classmethod
    def from_key(cls, key: Key) -> "Direction":
        match key:
            case Key.UP | Key.CTRL_UP:
                return cls.UP
            case Key.DOWN | Key.CTRL_DOWN:
                return cls.DOWN
            case Key.LEFT | Key.CTRL_LEFT:
                return cls.LEFT
            case Key.RIGHT | Key.CTRL_RIGHT:
                return cls.RIGHT


class NavigationMixin:
    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, App)
        super().__init__(*args, **kwargs)

    @singledispatchmethod
    @staticmethod
    def edge_center(widget_or_region: Widget | Region, direction: Direction) -> Offset:
        """
        Return the edge center of widget along direction

        TODO: Implement logic to offset slightly to account for visual perception vs geometric center
        """
        raise NotImplementedError(
            f"edge_center not implemented for type {type(widget_or_region)}"
        )

    @edge_center.register
    @staticmethod
    def _(widget: Widget, direction: Direction) -> Offset:
        x, y, width, height = widget.region

        # Get edge center from widget, or compute by ourselves
        if hasattr(widget, "edge_center"):
            edge_center = widget.edge_center(direction)
        else:
            region = Region(x, y, width, height)
            edge_center = NavigationMixin.edge_center(region, direction)

        # Ensure that edge_center is physically in widget
        assert widget.region.contains(
            edge_center.x, edge_center.y
        ), f"{edge_center} not in {widget.region}!!!"
        return edge_center

    @edge_center.register
    @staticmethod
    def _(region: Region, direction: Direction) -> Offset:
        x, y, width, height = region
        # Adding width,height to x,y will make them go outside the widget,
        # We need to add like "x+width-1" and "y+height-1"
        height = max(height - 1, 0)
        width = max(width - 1, 0)

        match direction:
            case Direction.UP:
                return Offset(int(x + width / 2), y)
            case Direction.DOWN:
                return Offset(int(x + width / 2), y + height)
            case Direction.LEFT:
                return Offset(x, int(y + height / 2))
            case Direction.RIGHT:
                return Offset(x + width, int(y + height / 2))

    @staticmethod
    def spacing(direction: Direction, widget: Widget) -> int:
        """
        Return spacing (distance to edge of screen) from widget along direction
        """
        screen = widget.app.screen
        spacing = screen.region.get_spacing_between(widget.region)
        match direction:
            case Direction.UP:
                return spacing.top
            case Direction.DOWN:
                return spacing.bottom
            case Direction.LEFT:
                return spacing.left
            case Direction.RIGHT:
                return spacing.right

    @staticmethod
    def step(direction: Direction) -> Offset:
        """Get unit step along direction of navigation"""
        match direction:
            case Direction.UP:
                return Offset(+0, -1)
            case Direction.DOWN:
                return Offset(+0, +1)
            case Direction.LEFT:
                return Offset(-1, +0)
            case Direction.RIGHT:
                return Offset(+1, +0)

    @staticmethod
    def perpendicular_step(direction: Direction) -> Offset:
        """Get unit step perpendicular to direction of navigation"""
        # We return unit step without direction, hence we return unsigned/absolute step
        # Direction handling is taken care by spiral_order generator, which yields -i first, then yields i
        match direction:
            case Direction.UP | Direction.DOWN:
                return Offset(1, 0)
            case Direction.LEFT | Direction.RIGHT:
                return Offset(0, 1)

    @staticmethod
    def spiral_order(n: int):
        """Generate [0, -1, 1, -2, 2, ...] up to ±(width//2)"""
        yield 0
        for i in range(1, n + 1):
            yield -i
            yield i

    @dataclass
    class RayTraceState:
        source: Widget
        exit_point: Offset
        direction: Direction
        entry_point: Offset
        target: Widget

    @staticmethod
    def ray_trace(direction: Direction, widget: Widget) -> RayTraceState:
        """
        Trace along direction with expanding cone from source widget.

        Args:
            direction: direction of navigation
            widget: source widget to trace from
        """
        source_edge_center = NavigationMixin.edge_center(widget, direction)
        ray_step = NavigationMixin.step(direction)
        perp_step = NavigationMixin.perpendicular_step(direction)
        spacing = NavigationMixin.spacing(direction, widget)

        # Perform ray tracing in an expanding cone
        cone_angle_tangent = 0.1
        for ray_dist in range(1, spacing):
            max_perp_distance = int(ray_dist * cone_angle_tangent)
            for perp_dist in NavigationMixin.spiral_order(max_perp_distance):
                point = source_edge_center + ray_step * ray_dist + perp_step * perp_dist
                target = widget.screen.get_focusable_widget_at(*point)
                if target is not None and target != widget:
                    return NavigationMixin.RayTraceState(
                        source=widget,
                        exit_point=source_edge_center,
                        direction=direction,
                        entry_point=point,
                        target=target,
                    )
        raise NoMatches("No focusable widget found")

    @staticmethod
    def should_navigate(direction: Direction, widget: Widget) -> bool:
        navigate = True

        if hasattr(widget, "should_navigate"):
            navigate = navigate and widget.should_navigate(direction)

        return navigate

    def on_key(self, event: TextualKeyEvent) -> None:
        assert isinstance(self, App)

        try:
            key = Key.from_event(event)
            direction = Direction.from_key(key)
            force_navigate = key.has_ctrl()
            source = self.focused
            if source is None:
                raise ValueError("source is None!!!")
            if force_navigate or self.should_navigate(direction, source):
                ray_trace_state = self.ray_trace(direction, source)
                if hasattr(ray_trace_state.target, "navigate"):
                    ray_trace_state.target.navigate(ray_trace_state)
                else:
                    ray_trace_state.target.focus()
                logging.debug(f"Success in NavigationMixin, {ray_trace_state=}")
        except (ValueError, NoMatches) as e:
            logging.debug(f"Exception in NavigationMixin: {repr(e)}")
            return


# TODO: Replace monkey-patching of textual ContentTabs.edge_center with subclass
def content_tabs_edge_center(self: ContentTabs, direction: Direction) -> Offset:
    x, y, width, height = self.region
    width = 0
    tabs = list(self.query(ContentTab))
    for tab in tabs:
        width += len(str(tab.label))
        width += tab.styles.padding.left
        width += tab.styles.padding.right
    region = Region(x, y, width, height)
    return NavigationMixin.edge_center(region, direction)


ContentTabs.edge_center = content_tabs_edge_center  # type: ignore[attr-defined]
