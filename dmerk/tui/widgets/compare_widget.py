from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label
from textual.reactive import reactive
from textual.events import Resize
from rich.text import Text

from dmerk.merkle import Merkle
from dmerk.utils import colorhash


def file_prefix(path: Path) -> str:
    if path.is_symlink():
        return "🔗 "
    elif path.is_dir():
        return "📁 "
    elif path.is_file():
        return "📄 "
    else:
        return "⭐ "


def colorhash_styled_text(text: str, digest: str) -> Text:
    return Text(str(text), style=f"bold grey11 on {colorhash(digest)}")


@dataclass
class Column:
    label: str
    key: str
    sort_key: Callable[[Merkle], Any]
    sort_reverse: bool


class Columns(Enum):
    @staticmethod
    def sort_by_path_name(m: Merkle) -> str:
        return m.path.name

    @staticmethod
    def sort_by_digest(m: Merkle) -> str:
        return m.digest

    NAME = Column("Name", "NAME", sort_by_path_name, False)
    DIGEST = Column("Digest", "DIGEST", sort_by_digest, False)


class CompareWidget(Widget):
    def __init__(
        self,
        path: Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        if path.is_file() and path.suffix == ".dmerk":
            self.merkle = Merkle.load(path)
        else:
            raise ValueError(f"path {path} must be a dmerk file")

    merkle_subpath: reactive[Path | None] = reactive(None)
    prev_cell_key = None
    sort_by = reactive(Columns.NAME.value.key)
    sort_reverse = reactive(Columns.NAME.value.sort_reverse)

    def __get_column_width(self, column_key: str) -> int | None:
        # The math here is to prevent horizontal scrollbar from appearing
        # The vertical scrollbar may take width of 2
        # Besides that, we have 2 columns, and we have to split the rem width amongst them
        # Each column has a built-in padding of 1 on both sides (see cell_padding in DataTable docs)
        N_COLS = 2
        TOTAL_AVAILABLE_WIDTH = self.size.width - 2 - 2 * N_COLS
        if self.size.width != 0:
            if column_key == Columns.DIGEST.value.key:
                return 32
            elif column_key == Columns.NAME.value.key:
                return TOTAL_AVAILABLE_WIDTH - 32
            else:
                raise ValueError(f"Unknown {column_key=}")
        else:
            return None

    @property
    def submerkle(self) -> Merkle:
        if self.merkle_subpath and self.merkle_subpath != self.merkle.path:
            return self.merkle.traverse(self.merkle_subpath.resolve())
        else:
            return self.merkle

    @property
    def label(self) -> str:
        maxlen = self.query_one(Label).size.width
        new_label = f"{self.submerkle.path}"
        if len(new_label) < maxlen:
            return new_label
        else:
            for p in reversed(self.submerkle.path.parents[:-1]):
                new_label = f".../{self.submerkle.path.relative_to(p)}"
                if len(new_label) < maxlen:
                    return new_label
        return ""

    async def _refresh_label(self) -> None:
        self.query_one(Label).update(Text(self.label, style="bold"))

    async def _refresh_table(self) -> None:
        compare_table = self.query_one(DataTable)
        compare_table.clear(columns=True)
        for column in Columns:
            compare_table.add_column(
                "\n" + column.value.label,
                key=column.value.key,
                width=self.__get_column_width(column_key=column.value.key),
            )
        if self.submerkle != self.merkle:
            compare_table.add_row(*["\n..", "\n-"], key="..", height=3)
        child_merkles = [m for m in self.submerkle.children.values()]
        child_merkles = sorted(
            child_merkles,
            key=Columns[self.sort_by].value.sort_key,
            reverse=self.sort_reverse,
        )
        for m in child_merkles:
            row = [
                Text("\n" + file_prefix(m.path))
                + colorhash_styled_text(m.path.name, m.digest),
                Text("\n") + colorhash_styled_text(m.digest, m.digest),
            ]
            compare_table.add_row(*row, key=str(m.path), height=3)

    async def watch_merkle_subpath(self) -> None:
        await self._refresh_label()
        await self._refresh_table()

    async def watch_sort_by(self) -> None:
        await self._refresh_label()
        await self._refresh_table()

    async def watch_sort_reverse(self) -> None:
        await self._refresh_label()
        await self._refresh_table()

    def compose(self) -> ComposeResult:
        yield Label(Text(f"{self.submerkle.path}", style="bold"))
        compare_table: DataTable[None] = DataTable(header_height=3)
        yield compare_table

    async def on_data_table_header_selected(
        self, message: DataTable.HeaderSelected
    ) -> None:
        if self.sort_by != message.column_key.value:
            if message.column_key.value is not None:
                self.sort_by = message.column_key.value
                self.sort_reverse = Columns[self.sort_by].value.sort_reverse
        else:
            self.sort_reverse = not self.sort_reverse

    def on_data_table_cell_selected(self, message: DataTable.CellSelected) -> None:
        if "NAME" in message.cell_key:
            if message.cell_key.row_key.value is not None:
                if self.prev_cell_key == message.cell_key:
                    p = Path(message.cell_key.row_key.value)
                    if p.is_dir():
                        if self.merkle_subpath:
                            self.merkle_subpath = (self.merkle_subpath / p).resolve()
                        else:
                            self.merkle_subpath = p
        self.prev_cell_key = message.cell_key

    async def on_resize(self, event: Resize) -> None:
        await self._refresh_label()
        await self._refresh_table()
