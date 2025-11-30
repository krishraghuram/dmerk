from textual.coordinate import Coordinate
from textual.widget import Widget
from textual.widgets import DataTable as TextualDataTable
from textual.widgets.data_table import CellType

from dmerk.tui.navigation import Direction


class DataTable(TextualDataTable[CellType]):

    prev_cursor_coordinate = Coordinate(0, 0)

    def watch_cursor_coordinate(
        self, old_cursor_coordinate: Coordinate, new_cursor_coordinate: Coordinate
    ) -> None:
        self.prev_cursor_coordinate = old_cursor_coordinate
        super().watch_cursor_coordinate(old_cursor_coordinate, new_cursor_coordinate)

    def should_navigate(self, direction: Direction) -> bool:
        """
        Return true if at DataTable's cursor is at the edge, to allow App's NavigationMixin to do it's magic

        Problem: Arrow key events are processed by DataTable first, then bubble up to App's NavigationMixin
        This causes double-handling: DataTable moves its cursor AND NavigationMixin moves focus

        Example: User presses UP on row 1
        1. DataTable binding moves cursor: row 1 → row 0
        2. NavigationMixin sees cursor at row 0 and switches focus to another widget
        Result: Both actions happen when we only want one

        Solution: Check if cursor was ALREADY at edge before this key press
        We track prev_cursor_coordinate to detect if we were at the boundary
        Only navigate away if the previous position was also at the edge
        """
        match direction:
            case Direction.UP:
                return self.prev_cursor_coordinate.row == 0
            case Direction.DOWN:
                return self.prev_cursor_coordinate.row == len(self.rows) - 1
            case Direction.LEFT:
                return self.prev_cursor_coordinate.column == 0
            case Direction.RIGHT:
                return self.prev_cursor_coordinate.column == len(self.columns) - 1
