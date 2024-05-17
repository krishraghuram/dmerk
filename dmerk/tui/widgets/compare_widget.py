from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label
from textual.reactive import reactive
from textual.events import Resize
from textual.css.query import NoMatches
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
    return Text(str(text), style=f"bold grey11 on {colorhash(digest)}", no_wrap=True)

@dataclass
class Column:
    label: str
    key: str


class Columns(Enum):
    NAME = Column("Name", "NAME")
    DIGEST = Column("Digest", "DIGEST")


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

    def __get_other_compare_widget(self) -> 'CompareWidget|None':
        if self.id == "compare-left":
            other_id = "compare-right"
        elif self.id == "compare-right":
            other_id = "compare-left"
        else:
            raise ValueError(f"Unexpected id {self.id}")
        if self.parent:
            try:
                return self.parent.query_one(f"#{other_id}", CompareWidget)
            except NoMatches as e:
                logging.info(f"No Matches for {other_id}")
                return None
        else:
            raise ValueError(f"self.parent is None")

    def __get_column_width(self, column_key: str) -> int:
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
            return 0

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
    
    async def _refresh(self) -> None:
        await self._refresh_label()
        await self._refresh_table()
        other_compare_widget = self.__get_other_compare_widget()
        if other_compare_widget:
            await other_compare_widget._refresh_label()
            await other_compare_widget._refresh_table()

    async def _refresh_label(self) -> None:
        self.query_one(Label).update(Text(self.label, style="bold"))

    def __get_compare_table_row(self, m: Merkle, match: bool):
        ncw = self.__get_column_width(column_key="NAME") # name column width
        dcw = self.__get_column_width(column_key="DIGEST") # digest column width
        if not match:
            ncw = dcw = 0
        row = [
            colorhash_styled_text(
                (
                    " "*(ncw)+"\n"
                    +file_prefix(m.path)+m.path.name+" "*(ncw-len(m.path.name)-3)+"\n"
                    +" "*(ncw)
                ),
                m.digest),
            colorhash_styled_text(
                (
                    " "*(dcw)+"\n"
                    +m.digest+" "*(dcw-len(m.digest))+"\n"
                    +" "*(dcw)
                ),
                m.digest),
        ]
        return row
    
    def __get_matches(self):
        other = self.__get_other_compare_widget()
        if other:
            digests_1 = set([m.digest for m in self.submerkle.children.values()])
            digests_2 = set([m.digest for m in other.submerkle.children.values()])
            matches = digests_1 & digests_2
            return matches
        else:
            return set()

    async def _refresh_table(self) -> None:
        compare_table = self.query_one(DataTable)
        compare_table.clear(columns=True)
        for column in Columns:
            compare_table.add_column(
                "\n" + column.value.label,
                key=column.value.key,
                width=self.__get_column_width(column_key=column.value.key),
            )
        child_merkles = [m for m in self.submerkle.children.values()]
        child_merkles = sorted(child_merkles, key=lambda m: m.digest)
        for m in child_merkles:
            if m.digest in self.__get_matches():
                row = self.__get_compare_table_row(m, match=True)
                compare_table.add_row(*row, key=str(m.path), height=3)
        for m in child_merkles:
            if m.digest not in self.__get_matches():
                row = self.__get_compare_table_row(m, match=False)
                compare_table.add_row(*row, key=str(m.path), height=3)
        if self.submerkle != self.merkle:
            compare_table.add_row(*["\n..", "\n-"], key="..", height=3)


    def compose(self) -> ComposeResult:
        yield Label(Text(f"{self.submerkle.path}", style="bold"))
        compare_table: DataTable[None] = DataTable(header_height=3)
        yield compare_table

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
                else:
                    self.prev_cell_key = message.cell_key
    
    async def watch_merkle_subpath(self) -> None:
        await self._refresh()

    async def on_resize(self, event: Resize) -> None:
        await self._refresh()
