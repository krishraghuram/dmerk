import logging
from enum import Enum
from typing import Any, cast

from textual.app import App
from textual.css.query import NoMatches
from textual.events import Key
from textual.geometry import Offset, Region, Size
from textual.widget import Widget
from textual.widgets import DataTable, Input
from textual.widgets._tabbed_content import ContentTabs


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


class NavigationMixin:
    def __init__(self, *args: Any, **kwargs: Any):
        assert isinstance(self, App)
        super().__init__(*args, **kwargs)

    @staticmethod
    def edge_center(direction: Direction, widget: Widget) -> Offset:
        """
        Return the edge center of widget along direction

        TODO: Implement logic to offset slightly to account for visual perception vs geometric center
        """
        x, y, width, height = widget.region

        # Special Cases (maybe impl visual center logic can help removing special cases)
        # ContentTabs and Input take full width of screen, but the text is only few characters
        if isinstance(widget, ContentTabs):
            width = 20
        elif isinstance(widget, Input):
            width = 15

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
    def ray_trace(direction: Direction, widget: Widget) -> Widget:
        """
        Trace along the given direction from given source widget and return the target widget to receive focus
        """
        source_edge_center = NavigationMixin.edge_center(direction, widget)
        step = NavigationMixin.step(direction)
        spacing = NavigationMixin.spacing(direction, widget)
        for i in range(1, spacing):
            offset = source_edge_center + step * i
            target = widget.screen.get_focusable_widget_at(*offset)
            if target is not None and target != widget:
                return target
        raise NoMatches("No focusable widget found")

    @staticmethod
    def should_navigate(direction: Direction, widget: Widget) -> bool:
        navigate = True

        if hasattr(widget, "should_navigate"):
            navigate = navigate and widget.should_navigate(direction)

        return navigate

    def on_key(self, event: Key) -> None:
        assert isinstance(self, App)

        try:
            direction = Direction.from_key(event.key)
            source = self.focused
            if source is None:
                raise ValueError("source is None!!!")
            if self.should_navigate(direction, source):
                target = self.ray_trace(direction, source)
                target.focus()
                logging.debug(f"{direction=}, {source=}, {target=}")
        except (ValueError, NoMatches) as e:
            logging.warning(str(e))
            return
