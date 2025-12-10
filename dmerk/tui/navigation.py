import logging
from typing import Any, cast
from enum import Enum

from textual.widget import Widget
from textual.widgets import RichLog, Button
from textual.geometry import Size, Region, Offset
from textual.events import Key
from textual.css.query import NoMatches


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
        assert isinstance(self, Widget)
        super().__init__(*args, **kwargs)

    def edge_center(self, direction: Direction, widget: Widget) -> Offset:
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

    def spacing(self, direction: Direction, widget: Widget) -> int:
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

    def step(self, direction: Direction) -> Offset:
        match direction:
            case Direction.UP:
                return Offset(+0, -1)
            case Direction.DOWN:
                return Offset(+0, +1)
            case Direction.LEFT:
                return Offset(-1, +0)
            case Direction.RIGHT:
                return Offset(+1, +0)

    def ray_trace(self, direction: Direction, widget: Widget) -> Widget:
        """
        Trace along the given direction from given source widget and return the target widget to receive focus
        """
        source_edge_center = self.edge_center(direction, widget)
        step = self.step(direction)
        spacing = self.spacing(direction, widget)
        for i in range(1, spacing):
            offset = source_edge_center + step * i
            target = widget.screen.get_focusable_widget_at(*offset)
            if target is not None and target != widget:
                return target
        raise NoMatches("No focusable widget found")

    def on_key(self, event: Key) -> None:
        assert isinstance(self, Widget)
        from dmerk.tui.app import DmerkApp

        try:
            direction = Direction.from_key(event.key)
            source = self.app.focused
        except ValueError as e:
            logging.warning(str(e))
            return
        try:
            target = self.ray_trace(direction, self)
            logging.debug(f"{direction=}, source={self}, {target=}")
            target.focus()
            event.stop()
        except NoMatches as e:
            logging.warning("No matches found!!!")
            return
