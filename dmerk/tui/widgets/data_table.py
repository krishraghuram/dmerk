import logging
from textual.coordinate import Coordinate
from textual.geometry import Offset, Region
from textual.widget import Widget
from textual.widgets import DataTable as TextualDataTable
from textual.widgets.data_table import CellType

from dmerk.tui.navigation import Direction, NavigationMixin


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

    def edge_center(self, direction: Direction) -> Offset:
        """
        Return the physical screen coordinates of the edge center of the DataTable widget in the given direction,
        aligned with the currently highlighted cell.

        The calculation involves three coordinate transformations:
        Table coordinates (row, column), to,
        Virtual terminal coordinates (x, y) via _get_cell_region, to,
        Physical terminal coordinates relative to current widget (self) by subtracting scroll_offset, to,
        Physical terminal coordinates relative to screen by adding self.region.offset

        Once we have the cell's physical screen coordinates, we compute the edge center of the entire
        DataTable widget in the given direction, but keep the perpendicular coordinate from the cell's edge center.
        This creates a "projected" point from the cursor toward the widget's edge.

        Example:
        Currently highlighted cell is shaded as ░
        cursor_edge_center is the x,y coordinate of the edge center of the currently highlighted cell.
        Depending on the direction (UP, DOWN, LEFT, RIGHT),
        we return the coordinates marked by ⇡ ⇣ ⇠ ⇢ respectively
        ```
          (x, y)
            ┌────⇡─────┬──────────┐ ▲
            │    ┆     │          │ │
            ├──────────┼──────────┤ │
            ⇠┄┄┄┄░┄┄┄┄┄│┄┄┄┄┄┄┄┄┄┄⇢ │
            ├──────────┼──────────┤ height
            │    ┆     │          │ │
            ├──────────┼──────────┤ │
            │    ┆     │          │ │
            └────⇣─────┴──────────┘ ▼
            ◀─────── width ──────▶
        ```
        """
        table_offset = self.region.offset
        cursor_region = self._get_cell_region(self.cursor_coordinate)
        cursor_offset = cursor_region.offset
        scroll_offset = self.scroll_offset
        offset = table_offset + cursor_offset - scroll_offset
        abs_cursor_region = Region(
            offset.x, offset.y, cursor_region.width, cursor_region.height
        )
        cursor_edge_center = NavigationMixin.edge_center(abs_cursor_region, direction)
        x, y, width, height = self.region
        height = max(height - 1, 0)
        width = max(width - 1, 0)
        match direction:
            case Direction.UP:
                table_edge_center = Offset(cursor_edge_center.x, y)
            case Direction.DOWN:
                table_edge_center = Offset(cursor_edge_center.x, y + height)
            case Direction.LEFT:
                table_edge_center = Offset(x, cursor_edge_center.y)
            case Direction.RIGHT:
                table_edge_center = Offset(x + width, cursor_edge_center.y)
        return table_edge_center

    def navigate(self, ray_trace_state: NavigationMixin.RayTraceState) -> None:
        """
        Set focus to self and attempt to set cursor coordinate based on navigation entry point

        We are able to set the cursor coordinate by piggy backing on the fact that DataTable
        attaches row,column coordinates to each cell's styles, as a "meta" attribute.

        Thus, to go in the reverse direction, from ray_trace_state.entry_point,
        we can use screen.get_style_at API to get the styles,
        and use its meta attribute to get the cursor coordinates (row,column)

        References:
        [Setting styles.meta with row,column in DataTable._render_cell](https://github.com/Textualize/textual/blob/0b7a5a7512a8486c092aa23153795cfafdf4abcb/src/textual/widgets/_data_table.py#L2135)
        [Usage of meta in _on_mouse_move to set hover_coordinate](https://github.com/Textualize/textual/blob/0b7a5a7512a8486c092aa23153795cfafdf4abcb/src/textual/widgets/_data_table.py#L2546)
        [Usage of meta in _on_click to set cursor_coordinate](https://github.com/Textualize/textual/blob/0b7a5a7512a8486c092aa23153795cfafdf4abcb/src/textual/widgets/_data_table.py#L2670)
        """
        try:
            styles = self.screen.get_style_at(*ray_trace_state.entry_point)
            meta = styles.meta
            self.cursor_coordinate = Coordinate(meta["row"], meta["column"])
        except Exception as e:
            logging.warning(
                f"Failed to set cursor_coordinate in DataTable.navigate: {e}"
            )
        finally:
            self.focus()
