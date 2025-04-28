from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import functools

from textual import work
from textual.worker import Worker, WorkerState
from textual.app import ComposeResult
from textual.widget import Widget
from textual.dom import DOMNode
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


# Bug: https://trello.com/c/iizCU2oj
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

    merkle_subpath: reactive[Path | None] = reactive(None)
    prev_cell_key = None

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
        self.loading = True
        if path.is_file() and path.suffix == ".dmerk":
            self._main(path)
        else:
            raise ValueError(f"path {path} must be a dmerk file")

    def reset_to_filepicker(self):
        from dmerk.tui.widgets.file_picker import FilePicker

        id_ = self.id.split("-")[-1] if self.id else ""
        id_ = "-".join(["filepicker", id_])
        logging.debug(id_)
        self.parent.mount(FilePicker(id=id_), after=self)
        self.remove()

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        self.merkle = Merkle.load(path)

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self.loading = False
            await self.recompose()
            await self._refresh()
        elif event.state in [WorkerState.ERROR, WorkerState.CANCELLED]:
            raise Exception("Worker failed/cancelled")

    def compose(self) -> ComposeResult:
        if not self.loading:
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
        self.prev_cell_key = message.cell_key

    async def watch_merkle_subpath(self) -> None:
        await self._refresh()

    async def on_resize(self, event: Resize) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        if not self.loading:
            await self._refresh_label()
            await self._refresh_table()
            other_compare_widget = CompareWidget._get_other_compare_widget(
                self.id, self.parent
            )
            if other_compare_widget:
                if not other_compare_widget.loading:
                    await other_compare_widget._refresh_label()
                    await other_compare_widget._refresh_table()

    async def _refresh_label(self) -> None:
        self.query_one(Label).update(Text(self.label, style="bold"))

    async def _refresh_table(self) -> None:
        compare_table = self.query_one(DataTable)
        compare_table.clear(columns=True)
        for column in Columns:
            compare_table.add_column(
                "\n" + column.value.label,
                key=column.value.key,
                width=CompareWidget._get_column_width(
                    self.size.width, column_key=column.value.key
                ),
            )
        matches = self._get_matches()
        child_merkles = [m for m in self.submerkle.children.values()]
        child_merkles = sorted(child_merkles, key=lambda m: m.digest)
        for m in child_merkles:
            if m.digest in matches:
                row = self._get_compare_table_row(m, match=True)
                compare_table.add_row(*row, key=str(m.path), height=3)
        for m in child_merkles:
            if m.digest not in matches:
                row = self._get_compare_table_row(m, match=False)
                compare_table.add_row(*row, key=str(m.path), height=3)
        if self.submerkle != self.merkle:
            compare_table.add_row(*["\n..", "\n-"], key="..", height=3)

    @staticmethod
    def _get_other_compare_widget(
        self_id: str | None, parent_widget: DOMNode | None
    ) -> "CompareWidget|None":
        if self_id == "compare-left":
            other_id = "compare-right"
        elif self_id == "compare-right":
            other_id = "compare-left"
        else:
            raise ValueError(f"Unexpected id {self_id}")
        if parent_widget:
            try:
                return parent_widget.query_one(f"#{other_id}", CompareWidget)
            except NoMatches:
                logging.debug(f"No Matches for {other_id}")
                return None
        else:
            raise ValueError("self.parent is None")

    @staticmethod
    @functools.lru_cache
    def _get_column_width(total_width: int, column_key: str) -> int:
        # The math here is to prevent horizontal scrollbar from appearing
        # The vertical scrollbar may take width of 2
        # Besides that, we have 2 columns, and we have to split the rem width amongst them
        # Each column has a built-in padding of 1 on both sides (see cell_padding in DataTable docs)
        N_COLS = 2
        TOTAL_AVAILABLE_WIDTH = total_width - 2 - 2 * N_COLS
        if total_width != 0:
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

    def _get_compare_table_row(self, m: Merkle, match: bool) -> list[Text]:
        ncw = CompareWidget._get_column_width(
            self.size.width, column_key="NAME"
        )  # name column width
        dcw = CompareWidget._get_column_width(
            self.size.width, column_key="DIGEST"
        )  # digest column width
        if not match:
            ncw = dcw = 0
        row = [
            colorhash_styled_text(
                (
                    " " * (ncw)
                    + "\n"
                    + file_prefix(m.path)
                    + m.path.name
                    + " " * (ncw - len(m.path.name) - 3)
                    + "\n"
                    + " " * (ncw)
                ),
                m.digest,
            ),
            colorhash_styled_text(
                (
                    " " * (dcw)
                    + "\n"
                    + m.digest
                    + " " * (dcw - len(m.digest))
                    + "\n"
                    + " " * (dcw)
                ),
                m.digest,
            ),
        ]
        return row

    def _get_matches(self) -> set[str]:
        other = CompareWidget._get_other_compare_widget(self.id, self.parent)
        if other:
            if self.loading or other.loading:
                return set()
            else:
                digests_1 = set([m.digest for m in self.submerkle.children.values()])
                digests_2 = set([m.digest for m in other.submerkle.children.values()])
                matches = digests_1 & digests_2
                return matches
        else:
            return set()
