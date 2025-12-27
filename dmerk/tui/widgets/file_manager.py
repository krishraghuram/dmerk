import itertools
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from humanize import naturaltime
from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import Resize
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input
from textual.widgets.data_table import CellDoesNotExist

from dmerk.tui.widgets import Breadcrumbs, ClearableInput, DataTable, FavoritesSidebar
from dmerk.utils import fuzzy_match, prefix_symbol_path

TIME_FORMATS: dict[str, Callable[[float], str]] = {
    "HUMAN_FRIENDLY": lambda timestamp: naturaltime(datetime.fromtimestamp(timestamp)),
    "ISO8601": lambda timestamp: datetime.fromtimestamp(timestamp).isoformat(),
}
TIME_FORMAT_CYCLER = itertools.cycle(list(TIME_FORMATS.keys()))


@dataclass
class Column:
    label: str
    key: str
    sort_key: Callable[[Path], str | datetime]
    sort_reverse: bool


class Columns(Enum):
    NAME = Column("Name", "NAME", lambda p: str.casefold(p.name), False)
    MODIFIED = Column(
        "Modified",
        "MODIFIED",
        lambda p: datetime.fromtimestamp(p.stat().st_ctime),
        True,
    )


class FileManager(Widget):

    BINDINGS = [
        ("f", "favorite", "Favorite"),
    ]

    path = reactive(Path.home())
    cursor_path: reactive[Path | None] = reactive(None, bindings=True)
    time_format = reactive(next(TIME_FORMAT_CYCLER))
    sort_by = reactive(Columns.MODIFIED.value.key)
    sort_reverse = reactive(Columns.MODIFIED.value.sort_reverse)
    filter_by = reactive("")

    @property
    def sort_key(self) -> Callable[[Path], str | datetime]:
        return Columns[self.sort_by].value.sort_key

    def compose(self) -> ComposeResult:
        yield ClearableInput(placeholder="Filter by...")
        yield Breadcrumbs(str(self.path))
        files_table: DataTable[None] = DataTable(header_height=3)
        yield files_table

    def on_input_changed(self, message: Input.Changed) -> None:
        self.filter_by = message.value

    def on_mount(self) -> None:
        dt = self.query_one(DataTable)

        def watch_hover_coordinate(old: Coordinate, new: Coordinate) -> None:
            try:
                dt.tooltip = dt.get_cell_at(new).strip()
            except:
                pass

        self.watch(dt, "hover_coordinate", watch_hover_coordinate)

        def watch_cursor_coordinate(old: Coordinate, new: Coordinate) -> None:
            try:
                cell_key = dt.coordinate_to_cell_key(new)
            except CellDoesNotExist:
                self.cursor_path = None
            else:
                if Columns.NAME.name in cell_key:
                    if cell_key.row_key.value is not None:
                        self.cursor_path = (
                            self.path / cell_key.row_key.value
                        ).resolve()
                    else:
                        self.cursor_path = None
                else:
                    self.cursor_path = None

        self.watch(dt, "cursor_coordinate", watch_cursor_coordinate)

    def __get_column_width(self) -> int | None:
        if self.size.width != 0:
            # the math is to prevent horizontal scrollbar from appearing
            return int((self.size.width - 2) / 2) - 2
        else:
            return None

    async def _refresh(self) -> None:
        await self._refresh_breadcrumbs()
        await self._refresh_table()

    def on_breadcrumbs_changed(self, event: Breadcrumbs.Changed) -> None:
        self.path = Path("".join(event.parts))

    async def _refresh_breadcrumbs(self) -> None:
        breadcrumb_parts = ["/"]
        breadcrumb_parts = breadcrumb_parts + [f"{p}/" for p in self.path.parts[1:]]
        self.query_one(Breadcrumbs).update(parts=breadcrumb_parts)

    def _get_header_label(self, column: Column) -> str:
        if self.sort_by == column.key:
            return "\n" + column.label + (" ▾" if self.sort_reverse else " ▴")
        else:
            return "\n" + column.label

    async def _refresh_table(self) -> None:
        files_table = self.query_one(DataTable)
        files_table.clear(columns=True)
        for column in Columns:
            files_table.add_column(
                self._get_header_label(column.value),
                key=column.value.key,
                width=self.__get_column_width(),
            )
        files_table.add_row(*["\n..", "\n-"], key="..", height=3)
        files_list = [p for p in self.path.iterdir() if p.exists()]
        files_list = [p for p in files_list if fuzzy_match(p.name, self.filter_by)]
        files_list = sorted(
            files_list,
            key=self.sort_key,
            reverse=self.sort_reverse,
        )
        for file in files_list:
            files_table.add_row(
                *[
                    "\n" + prefix_symbol_path(file) + file.name,
                    "\n" + TIME_FORMATS[self.time_format](file.stat().st_ctime),
                ],
                key=str(file),
                height=3,
            )
        # Prevent Vertical Scrollbar
        # Logic is, we set files_table height to self height - sum of heights of other widgets
        files_table.styles.height = self.size.height - sum(
            [w.size.height for w in self.query_children() if w != files_table]
        )

    async def on_resize(self, event: Resize) -> None:
        await self._refresh()

    async def watch_path(self, new_path: Path) -> None:
        self.query_one(ClearableInput).clear()
        self.post_message(FileManager.PathChange(new_path))
        await self._refresh()

    async def watch_time_format(self) -> None:
        files_table = self.query_one(DataTable)
        cursor_position = files_table.cursor_coordinate
        await self._refresh()
        files_table.move_cursor(**cursor_position._asdict())

    async def watch_filter_by(self) -> None:
        await self._refresh()

    async def watch_sort_by(self) -> None:
        await self._refresh()

    async def watch_sort_reverse(self) -> None:
        await self._refresh()

    async def on_data_table_header_selected(
        self, message: DataTable.HeaderSelected
    ) -> None:
        if self.sort_by != message.column_key.value:
            if message.column_key.value is not None:
                self.sort_by = message.column_key.value
                self.sort_reverse = Columns[self.sort_by].value.sort_reverse
        else:
            self.sort_reverse = not self.sort_reverse

    class PathChange(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "favorite":
                return (
                    self.app.query_one(FavoritesSidebar).can_add_favorite()
                    and self.cursor_path is not None
                    and self.cursor_path.is_dir()
                )
            case _:
                return True

    def action_favorite(self) -> None:
        assert self.cursor_path is not None
        self.app.query_one(FavoritesSidebar).add_favorite(self.cursor_path)
        self.refresh_bindings()

    def on_data_table_cell_selected(self, message: DataTable.CellSelected) -> None:
        if Columns.NAME.name in message.cell_key:
            if message.cell_key.row_key.value is not None:
                new_path: Path = self.path / message.cell_key.row_key.value
                new_path = new_path.resolve()
                if new_path.is_dir():
                    self.path = new_path
        elif Columns.MODIFIED.name in message.cell_key:
            self.time_format = next(TIME_FORMAT_CYCLER)

    def path_selected(self, path: Path) -> None:
        self.path = path
