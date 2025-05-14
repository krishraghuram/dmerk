from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath
import logging
import functools
from collections import Counter
from typing import cast

from textual import work
from textual.worker import Worker, WorkerState
from textual.app import ComposeResult
from textual.widget import Widget
from textual.dom import DOMNode
from textual.widgets import DataTable, Label
from textual.widgets.data_table import RowKey
from textual.reactive import reactive
from textual.events import Resize, DescendantBlur, Click
from textual.css.query import NoMatches
from textual.coordinate import Coordinate
from textual.containers import Horizontal
from rich.text import Text

from dmerk.merkle import Merkle
from dmerk.utils import colorhash


def file_prefix(path: Merkle.Type) -> str:
    if path == Merkle.Type.SYMLINK:
        return "🔗 "
    elif path == Merkle.Type.DIRECTORY:
        return "📁 "
    elif path == Merkle.Type.FILE:
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

    merkle_subpath: reactive[PurePath | None] = reactive(None)
    prev_cell_key = None
    filter_by = reactive("")

    def filter(self, m: Merkle) -> bool:
        # TODO: Implement fuzzy match
        if self.filter_by:
            return self.filter_by.casefold() in m.path.name.casefold()
        else:
            return True

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

    def reset_to_filepicker(self) -> None:
        from dmerk.tui.widgets.file_picker import FilePicker

        id_ = self.id.split("-")[-1] if self.id else ""
        id_ = "-".join(["filepicker", id_])
        cast(Widget, self.parent).mount(FilePicker(id=id_), after=self)
        self.remove()

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        self.merkle = Merkle.load(path)

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self.loading = False
            await self.recompose()
            await self._add_watches()
            await self._refresh()
        elif event.state in [WorkerState.ERROR, WorkerState.CANCELLED]:
            raise Exception("Worker failed/cancelled")

    def compose(self) -> ComposeResult:
        if not self.loading:
            yield Horizontal(Label(Text(f"{self.merkle.path}", style="bold")))
            compare_table: DataTable[None] = DataTable(header_height=3)
            yield compare_table

    def on_data_table_cell_selected(self, message: DataTable.CellSelected) -> None:
        if "NAME" in message.cell_key:
            if self.prev_cell_key == message.cell_key:
                path = message.cell_key.row_key.value
                if path == "..":
                    if self.merkle_subpath:
                        self.merkle_subpath = self.merkle_subpath.parent
                    else:
                        raise ValueError(
                            "Illegal state, cannot go above the root merkle"
                        )
                elif path is not None:
                    pure_path = PurePath(path)
                    if self.submerkle.children[pure_path].type == Merkle.Type.DIRECTORY:
                        if self.merkle_subpath:
                            self.merkle_subpath = self.merkle_subpath / pure_path
                        else:
                            self.merkle_subpath = pure_path
        self.prev_cell_key = message.cell_key

    def on_descendant_blur(self, message: DescendantBlur) -> None:
        self.prev_cell_key = None

    async def watch_filter_by(self) -> None:
        await self._refresh()

    async def watch_merkle_subpath(self) -> None:
        await self._refresh()

    async def on_resize(self, event: Resize) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        if not self.loading:
            await self._refresh_label()
            await self._refresh_table(force=True)
            other_compare_widget = CompareWidget._get_other_compare_widget(
                self.id, self.parent
            )
            if other_compare_widget:
                if not other_compare_widget.loading:
                    await other_compare_widget._refresh_label()
                    await other_compare_widget._refresh_table()

    def on_click(self, message: Click) -> None:
        if isinstance(message.widget, Label):
            labels = []
            for c in self.query_one(Horizontal).children:
                if isinstance(c, Label) and isinstance(c.renderable, Text):
                    labels.append(c)
            idx = labels.index(message.widget)
            merkle_subpath_parts = [
                cast(Text, l.renderable).plain for l in labels[: idx + 1]
            ]
            self.merkle_subpath = PurePath("".join(merkle_subpath_parts))

    async def _refresh_label(self) -> None:
        label_parts = [str(self.merkle.path)]
        label_parts = label_parts + [
            f"/{p}" for p in self.submerkle.path.relative_to(self.merkle.path).parts
        ]
        labels = [Label(Text(l, style="bold")) for l in label_parts]
        await self.query_one(Horizontal).remove_children()
        await self.query_one(Horizontal).mount_all(labels)

    async def _refresh_table(self, force: bool = False) -> None:
        matches = self._get_matches()
        compare_table = self.query_one(DataTable)
        # Check if we can do "partial refresh"
        if not force and len(matches) == 0:
            # Not a force refresh, and there are also no matches
            # Cells which were previously matches, will have solid background color
            # We need to update so that the solid bg color is removed now, since there are no matches
            # This requires removing the space char `" "` from the start and end of each line of each cell
            for r in range(len(compare_table.rows)):
                for c in range(len(compare_table.columns)):
                    cell_value: Text = compare_table.get_cell_at(Coordinate(r, c))
                    cell_value.plain = "\n".join(
                        [l.strip() for l in cell_value.plain.split("\n")]
                    )
                    compare_table.update_cell_at(Coordinate(r, c), cell_value)
            return  # prevent full refresh
        # Full Refresh Code Below
        compare_table.clear(columns=True)
        for column in Columns:
            compare_table.add_column(
                "\n" + column.value.label,
                key=column.value.key,
                width=CompareWidget._get_column_width(
                    self.size.width, column_key=column.value.key
                ),
            )
        child_merkles = [m for m in self.submerkle.children.values()]
        filtered_child_merkles = list(filter(self.filter, child_merkles))
        matching_child_merkles = sorted(
            filter(lambda m: m.digest in matches, filtered_child_merkles),
            key=lambda m: m.digest,
        )
        unmatched_child_merkles = sorted(
            filter(lambda m: m.digest not in matches, filtered_child_merkles),
            key=lambda m: m.digest,
        )
        for m in matching_child_merkles:
            total_height = matches[m.digest][0]
            count = matches[m.digest][1]
            height = int(total_height / count)
            matches[m.digest] = ((total_height - height), count - 1)
            row = self._get_compare_table_row(m, match=True, height=height)
            compare_table.add_row(*row, key=str(m.path), height=height)
        for m in unmatched_child_merkles:
            row = self._get_compare_table_row(m, match=False)
            compare_table.add_row(*row, key=str(m.path), height=3)

    def _get_merkle_from_row_key(self, row_key: RowKey) -> Merkle:
        child_merkles = [m for m in self.submerkle.children.values()]
        filtered_child_merkles = list(filter(self.filter, child_merkles))
        for m in filtered_child_merkles:
            if str(m.path) == row_key:
                return m
        else:
            raise ValueError(f"No merkle found for row key '{row_key}'")

    def _get_row_key_from_scroll_y(
        self, scroll_y: float, fully_visible: bool = False
    ) -> RowKey | None:
        """
        Return the row key of the row at scroll_y
        """
        y_offsets = self.query_one(DataTable)._y_offsets
        scroll_y = int(scroll_y)

        if fully_visible:
            # Return the first fully visible row after scroll_y
            for idx in range(len(y_offsets) - scroll_y):
                row_key, offset = y_offsets[scroll_y + idx]
                if offset == 0:
                    logging.debug(f"{row_key.value=}, {idx=}")
                    return row_key
                    break
            else:
                logging.debug("No matching entry")
                return None
        else:
            # Return the first visible (even partially visible) row after scroll_y
            try:
                row_key, _ = y_offsets[scroll_y]
                logging.debug(f"{row_key.value=}")
                return row_key
            except IndexError:
                return None

    # BUG: When clicking on a merkle subdirectory, the other CompareWidget gets reset to 0, and this makes navigation a pain
    async def _add_watches(self) -> None:
        def watch_scroll_y(old_scroll_y: float, new_scroll_y: float) -> None:
            logging.debug(
                f"watch_scroll_y in {self.id}: {old_scroll_y}, {new_scroll_y}"
            )
            # We only want to sync scroll when we are scrolling across matches
            # Once we reach unmatched merkles, we no longer want to sync scroll
            other = CompareWidget._get_other_compare_widget(self.id, self.parent)
            row_key = self._get_row_key_from_scroll_y(old_scroll_y)
            matches = self._get_matches()
            if other and row_key:
                m = self._get_merkle_from_row_key(row_key)
                if m.digest in matches:
                    other.query_one(DataTable).scroll_to(
                        None, new_scroll_y, animate=False
                    )

        self.watch(self.query_one(DataTable), "scroll_y", watch_scroll_y, init=False)

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
            return self.merkle.traverse(self.merkle_subpath)
        else:
            return self.merkle

    def _get_compare_table_row(
        self, m: Merkle, match: bool, height: int = 3
    ) -> list[Text]:
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
                    (" " * (ncw) + "\n") * int((height - 1) / 2)
                    + file_prefix(m.type)
                    + m.path.name
                    + " " * (ncw - len(m.path.name) - 3)
                    + ("\n" + " " * (ncw)) * (height - 1 - int((height - 1) / 2))
                ),
                m.digest,
            ),
            colorhash_styled_text(
                (
                    (" " * (dcw) + "\n") * int((height - 1) / 2)
                    + m.digest
                    + " " * (dcw - len(m.digest))
                    + ("\n" + " " * (dcw)) * (height - 1 - int((height - 1) / 2))
                ),
                m.digest,
            ),
        ]
        return row

    def _get_matches(self) -> dict[str, tuple[int, int]]:
        other = CompareWidget._get_other_compare_widget(self.id, self.parent)
        if other:
            if self.loading or other.loading:
                return dict()
            else:
                digests_1 = [m.digest for m in self.submerkle.children.values()]
                digests_2 = [m.digest for m in other.submerkle.children.values()]
                intersection = set(digests_1) & set(digests_2)
                counter_1 = Counter(digests_1)
                counter_2 = Counter(digests_2)
                matches = {
                    i: (3 * max(counter_1[i], counter_2[i]), counter_1[i])
                    for i in intersection
                }
                return matches
        else:
            return dict()
