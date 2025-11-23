from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import Resize
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable

import dmerk.constants as constants
from dmerk.tui.widgets.compare_widget import CompareWidget
from dmerk.utils import fuzzy_match, prefix_symbol_path
from dmerk.tui.navigation import NavigationMixin


class FilePicker(NavigationMixin, Widget):

    filter_by = reactive("")

    def __init__(
        self,
        path: Path | None = None,
        *,
        filter_by: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        if not path:
            # path = Path(constants.APP_STATE_PATH) / ".." / "0.3.0" / "OLD" / "1"
            path = Path(constants.APP_STATE_PATH) / ".." / "0.3.0" / "IMP"
        if path.is_dir():
            self.path = path
        else:
            raise ValueError(f"path {path} must be a directory")
        if filter_by:
            self.filter_by = filter_by

    path = reactive(Path.home())
    prev_cell_key = None

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
            return int(self.size.width - 2)
        else:
            return None

    async def _refresh_table(self) -> None:
        self.prev_cell_key = None
        files_table = self.query_one(DataTable)
        files_table.clear(columns=True)
        files_table.add_column("\nName", key="NAME", width=self.__get_column_width())
        files_table.add_row(*["\n.."], key="..", height=3)
        files_list = [p for p in self.path.iterdir() if p.exists()]
        files_list = [p for p in files_list if fuzzy_match(p.name, self.filter_by)]
        files_list = sorted(files_list, key=lambda p: str.casefold(p.name))
        for file in files_list:
            files_table.add_row(
                *["\n" + prefix_symbol_path(file) + file.name],
                key=str(file),
                height=3,
            )

    async def on_resize(self, event: Resize) -> None:
        await self._refresh_table()

    async def watch_path(self) -> None:
        await self._refresh_table()

    async def watch_filter_by(self) -> None:
        await self._refresh_table()

    def on_data_table_cell_highlighted(
        self, message: DataTable.CellHighlighted
    ) -> None:
        self.prev_cell_key = None

    async def _mount_compare_widget(self, path: Path) -> None:
        await cast(Widget, self.parent).mount(
            CompareWidget(path, filter_by=self.filter_by), after=self
        )
        await self.remove()
        self.call_after_refresh(
            cast(Widget, self.parent).query_one(CompareWidget).focus
        )

    async def on_data_table_cell_selected(
        self, message: DataTable.CellSelected
    ) -> None:
        if message.cell_key.row_key.value is not None:
            new_path: Path = self.path / message.cell_key.row_key.value
            new_path = new_path.resolve()
            if new_path.is_file():
                if self.prev_cell_key == message.cell_key:
                    if isinstance(self.parent, Widget):
                        await self._mount_compare_widget(new_path)
                    else:
                        raise ValueError(f"{self.parent=} is not a Widget!!!")
                else:
                    pass
            elif new_path.is_dir():
                if self.prev_cell_key == message.cell_key:
                    self.path = new_path
                else:
                    pass
        self.prev_cell_key = message.cell_key

    def path_selected(self, path: Path) -> None:
        self.path = path

    @property
    def highlighted_path(self) -> Path | None:
        files_table = self.query_one(DataTable)
        cell_key = files_table.coordinate_to_cell_key(files_table.cursor_coordinate)
        if cell_key.row_key.value is not None:
            highlighted_path = self.path / cell_key.row_key.value
            return highlighted_path.resolve()
        else:
            return None
