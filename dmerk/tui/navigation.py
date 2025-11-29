import logging
from typing import Any, cast
from enum import Enum

from textual.widget import Widget
from textual.widgets import DataTable
from textual.geometry import Size, Region, Offset
from textual.events import Key
from textual.css.query import NoMatches
from textual.app import App


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
        """
        # TODO: Implement logic to offset slightly to account for visual perception vs geometric center
        x, y, width, height = widget.region
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

        # For data tables, we should only navigate if we are at edge
        # BUG:
        #   DataTable gets Key event first and then it bubbles to us (App)
        #   So this means DataTable binding gets processed first before navigation code
        #   So when on data table row/col 1 / len()-2 , the binding is processed first, so row/col becomes 0 / len()-1
        #   And then our code also processes navigation, so we handle same event twice
        if isinstance(widget, DataTable):
            dt = widget
            match direction:
                case Direction.UP:
                    navigate = navigate and dt.cursor_row == 0
                case Direction.DOWN:
                    navigate = navigate and dt.cursor_row == len(dt.rows) - 1
                case Direction.LEFT:
                    navigate = navigate and dt.cursor_column == 0
                case Direction.RIGHT:
                    navigate = navigate and dt.cursor_column == len(dt.columns) - 1

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
