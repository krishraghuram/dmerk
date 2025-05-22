from dataclasses import dataclass
import itertools
from typing import Callable, Any
from enum import Enum

from pathlib import Path
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable
from textual.reactive import reactive
from textual.message import Message
from textual.coordinate import Coordinate
from textual.events import Resize, Focus, Key
from textual.binding import Binding

from .favorites_sidebar import FavoritesSidebar

from humanize import naturaltime


def file_prefix(path: Path) -> str:
    if path.is_symlink():
        return "🔗 "
    elif path.is_dir():
        return "📁 "
    elif path.is_file():
        return "📄 "
    else:
        return "⭐ "


TIME_FORMATS: dict[str, Callable[[float], str]] = {
    "HUMAN_FRIENDLY": lambda timestamp: naturaltime(datetime.fromtimestamp(timestamp)),
    "ISO8601": lambda timestamp: datetime.fromtimestamp(timestamp).isoformat(),
}
TIME_FORMAT_CYCLER = itertools.cycle(list(TIME_FORMATS.keys()))


@dataclass
class Column:
    label: str
    key: str
    sort_key: Callable[[Path], Any]
    sort_reverse: bool


class Columns(Enum):
    NAME = Column("Name", "NAME", lambda p: p.name, False)
    MODIFIED = Column(
        "Modified",
        "MODIFIED",
        lambda p: datetime.fromtimestamp(p.stat().st_ctime),
        True,
    )


class FileManager(Widget):
    path = reactive(Path.home())
    time_format = reactive(next(TIME_FORMAT_CYCLER))
    sort_by = reactive(Columns.MODIFIED.value.key)
    sort_reverse = reactive(Columns.MODIFIED.value.sort_reverse)
    prev_cell_key = None

    def on_key(self, event: Key):
        files_table = self.query_one(DataTable)
        if event.key == "left":
            if files_table.cursor_column == 0:
                print("Focusing Sidebar")
                self.screen.query_one(FavoritesSidebar).focus()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        files_table: DataTable[None] = DataTable(header_height=3)
        yield files_table

    def on_mount(self) -> None:
        dt = self.query_one(DataTable)

        def watch_hover_coordinate(old: Coordinate, new: Coordinate) -> None:
            try:
                dt.tooltip = dt.get_cell_at(new).strip()
            except:
                pass

        self.watch(dt, "hover_coordinate", watch_hover_coordinate)

    def __get_column_width(self) -> int | None:
        if self.size.width != 0:
            # the math is to prevent horizontal scrollbar from appearing
            return int((self.size.width - 2) / 2) - 2
        else:
            return None

    async def _refresh_table(self) -> None:
        self.prev_cell_key = None
        files_table = self.query_one(DataTable)
        files_table.clear(columns=True)
        for column in Columns:
            files_table.add_column(
                "\n" + column.value.label,
                key=column.value.key,
                width=self.__get_column_width(),
            )
        files_table.add_row(*["\n..", "\n-"], key="..", height=3)
        files_list = [p for p in self.path.iterdir() if p.exists()]
        files_list = sorted(
            files_list,
            key=Columns[self.sort_by].value.sort_key,
            reverse=self.sort_reverse,
        )
        for file in files_list:
            files_table.add_row(
                *[
                    "\n" + file_prefix(file) + file.name,
                    "\n" + TIME_FORMATS[self.time_format](file.stat().st_ctime),
                ],
                key=str(file),
                height=3,
            )

    async def on_resize(self, event: Resize) -> None:
        await self._refresh_table()

    async def watch_path(self) -> None:
        await self._refresh_table()

    async def watch_time_format(self) -> None:
        files_table = self.query_one(DataTable)
        cursor_position = files_table.cursor_coordinate
        await self._refresh_table()
        files_table.move_cursor(**cursor_position._asdict())

    async def watch_sort_by(self) -> None:
        await self._refresh_table()

    async def watch_sort_reverse(self) -> None:
        await self._refresh_table()

    async def on_data_table_header_selected(
        self, message: DataTable.HeaderSelected
    ) -> None:
        if self.sort_by != message.column_key.value:
            if message.column_key.value is not None:
                self.sort_by = message.column_key.value
                self.sort_reverse = Columns[self.sort_by].value.sort_reverse
        else:
            self.sort_reverse = not self.sort_reverse

    class PathSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    class PathChange(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def on_data_table_cell_highlighted(
        self, message: DataTable.CellHighlighted
    ) -> None:
        self.prev_cell_key = None

    def on_data_table_cell_selected(self, message: DataTable.CellSelected) -> None:
        if Columns.NAME.name in message.cell_key:
            if message.cell_key.row_key.value is not None:
                new_path: Path = self.path / message.cell_key.row_key.value
                new_path = new_path.resolve()
                if new_path.is_dir():
                    if self.prev_cell_key == message.cell_key:
                        self.path = new_path
                        self.post_message(FileManager.PathChange(new_path))
                    else:
                        self.post_message(FileManager.PathSelected(new_path))
        elif Columns.MODIFIED.name in message.cell_key:
            self.time_format = next(TIME_FORMAT_CYCLER)
        self.prev_cell_key = message.cell_key

    def path_selected(self, path: Path) -> None:
        self.path = path

    @property
    def highlighted_path(self) -> Path | None:
        files_table = self.query_one(DataTable)
        cell_key = files_table.coordinate_to_cell_key(files_table.cursor_coordinate)
        if Columns.NAME.name in cell_key:
            if cell_key.row_key.value is not None:
                highlighted_path = self.path / cell_key.row_key.value
                return highlighted_path.resolve()
            else:
                return None
        else:
            return None
