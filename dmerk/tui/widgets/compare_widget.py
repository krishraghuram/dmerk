from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath
import logging
import functools
from collections import Counter
from typing import Callable, cast

from textual import work
from textual.worker import Worker, WorkerState
from textual.app import ComposeResult
from textual.widget import Widget
from textual.dom import DOMNode
from textual.widgets import DataTable, Label, Button
from textual.widgets.data_table import RowKey
from textual.reactive import reactive, Reactive
from textual.events import DescendantBlur, Click, Resize
from textual.css.query import NoMatches
from textual.coordinate import Coordinate
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from rich.text import Text

from dmerk.merkle import Merkle
from dmerk.utils import colorhash, fuzzy_match


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
    sort_key: Callable[[Merkle], str]


class Columns(Enum):
    NAME = Column("Name", "NAME", lambda m: str.casefold(m.path.name))
    DIGEST = Column("Digest", "DIGEST", lambda m: m.digest)


class CompareWidget(Widget):

    BUTTON_RESET_COMPARE = "button-reset-compare"

    merkle_subpath: reactive[PurePath | None] = reactive(None)
    prev_cell_key = None
    filter_by = reactive("")
    sort_by: Reactive[None | str] = reactive(None)
    sort_reverse: Reactive[bool] = reactive(False)
    prev_screen_size: Reactive[Size | None] = reactive(None)

    @property
    def matches_sort_key(self) -> Callable[[Merkle], str]:
        # By default, we want to sort digest-matches by digest, so that matching items show up side-by-side
        if self.sort_by:
            return Columns[self.sort_by].value.sort_key
        else:
            return lambda m: m.digest

    @property
    def unmatched_sort_key(self) -> Callable[[Merkle], str]:
        # By default, we want to sort name-matches and unmatched by name,
        # so that user can scroll through them and find the item they are interested in quickly
        if self.sort_by:
            return Columns[self.sort_by].value.sort_key
        else:
            return lambda m: str.casefold(m.path.name)

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

    async def _reset_to_filepicker(self) -> None:
        from dmerk.tui.widgets.file_picker import FilePicker

        id_ = self.id.split("-")[-1] if self.id else ""
        id_ = "-".join(["filepicker", id_])
        cast(Widget, self.parent).mount(FilePicker(id=id_), after=self)
        await self.remove()

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        merkle = Merkle.load(path)
        # Create a virtual/dummy parent just so as to start rendering from root, instead root's children
        self.merkle = Merkle(
            path=merkle.path.parent,
            type=Merkle.Type.DIRECTORY,
            size=0,
            digest="",
            children={Path(merkle.path): merkle},
        )

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self.loading = False
            await self.recompose()
            await self._add_watches()
            self.call_after_refresh(self._refresh_when_ready)
        elif event.state in [WorkerState.ERROR, WorkerState.CANCELLED]:
            raise Exception("Worker failed/cancelled")

    async def _refresh_when_ready(self, attempt: int = 0) -> None:
        MAX_ATTEMPTS = 100
        if self.size.width > 0:
            await self._refresh()
        elif attempt < MAX_ATTEMPTS:
            self.call_after_refresh(lambda: self._refresh_when_ready(attempt + 1))
        else:
            logging.error(f"Widget {self.id} failed to initialize")

    def compose(self) -> ComposeResult:
        self.prev_screen_size = self.screen.size
        if not self.loading:
            compare_table: DataTable[None] = DataTable(header_height=3)
            yield Vertical(
                Horizontal(Label(Text(f"{self.merkle.path}", style="bold"))),
                compare_table,
                Button("RESET", "primary", id=self.BUTTON_RESET_COMPARE),
            )

    async def on_button_pressed(self, message: Button.Pressed) -> None:
        if message.button.id == self.BUTTON_RESET_COMPARE:
            await self._reset_to_filepicker()

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

    async def on_resize(self, event: Resize) -> None:
        if self.prev_screen_size != self.screen.size:
            await self._refresh()
        self.prev_screen_size = self.screen.size

    async def watch_filter_by(self) -> None:
        await self._refresh()

    async def watch_merkle_subpath(self) -> None:
        await self._refresh()

    async def watch_sort_by(self) -> None:
        self._sync_sort_fields()
        await self._refresh()

    async def watch_sort_reverse(self) -> None:
        self._sync_sort_fields()
        await self._refresh()

    async def on_data_table_header_selected(
        self, message: DataTable.HeaderSelected
    ) -> None:
        """
        Initially we have (sort_by,sort_reverse) as (None,False)
        Clicking on a column repeatedly, like clicking on Name several times,
            should lead to this pattern of length 3
            Note that we initially sort by NAME, then we reverse it,
            and then finally we reset back to default behavior of (None,False)
        Pattern: (NAME,False), (NAME,True), (None,False), (NAME,False), ...
        At any point, clicking on a new column should start the sequence from new columns,
            like if we click on Digest at some point, then it starts from,
        Pattern: (DIGEST,False), (DIGEST,True), (None,False), (DIGEST,False), ...
        """
        if self.sort_by != message.column_key.value:
            if message.column_key.value is not None:
                self.sort_by = message.column_key.value
                self.sort_reverse = False
        else:
            if self.sort_reverse is False:
                self.sort_reverse = True
            else:
                self.sort_by = None
                self.sort_reverse = False

    def on_click(self, message: Click) -> None:
        if isinstance(message.widget, Label):
            labels: list[Label] = []
            for c in self.query_one(Horizontal).children:
                if isinstance(c, Label) and isinstance(c.content, Text):
                    labels.append(c)
            idx = labels.index(message.widget)
            merkle_subpath_parts = [
                cast(Text, l.content).plain for l in labels[: idx + 1]
            ]
            self.merkle_subpath = PurePath("".join(merkle_subpath_parts))

    def _sync_sort_fields(self) -> None:
        other = CompareWidget._get_other_compare_widget(self.id, self.parent)
        if other:
            other.sort_by = self.sort_by
            other.sort_reverse = self.sort_reverse

    async def _refresh(self) -> None:
        if not self.loading:
            await self._refresh_label()
            await self._refresh_table(force=True)
            other = CompareWidget._get_other_compare_widget(self.id, self.parent)
            if other:
                if not other.loading:
                    await other._refresh_label()
                    await other._refresh_table()

    async def _refresh_label(self) -> None:
        label_parts = [str(self.merkle.path)]
        label_parts = label_parts + [
            f"/{p}" for p in self.submerkle.path.relative_to(self.merkle.path).parts
        ]
        labels = [Label(Text(l, style="bold")) for l in label_parts]
        await self.query_one(Horizontal).remove_children()
        await self.query_one(Horizontal).mount_all(labels)

    def _get_header_label(self, column: Column) -> str:
        if self.sort_by == column.key:
            return "\n" + column.label + (" ▾" if self.sort_reverse else " ▴")
        else:
            return "\n" + column.label

    async def _refresh_table(self, force: bool = False) -> None:
        matches = self._get_matches()
        name_matches = self._get_name_matches()
        compare_table = self.query_one(DataTable)
        # Check if we can do "partial refresh"
        if not force and len(matches) == 0 and len(name_matches) == 0:
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
                self._get_header_label(column.value),
                key=column.value.key,
                width=CompareWidget._get_column_width(
                    self.size.width, column_key=column.value.key
                ),
            )
        child_merkles = [m for m in self.submerkle.children.values()]
        filtered_child_merkles = [
            m for m in child_merkles if fuzzy_match(m.path.name, self.filter_by)
        ]
        matching_child_merkles = sorted(
            filter(lambda m: m.digest in matches, filtered_child_merkles),
            key=self.matches_sort_key,
            reverse=self.sort_reverse,
        )
        unmatched_child_merkles = sorted(
            filter(lambda m: m.digest not in matches, filtered_child_merkles),
            key=self.unmatched_sort_key,
            reverse=self.sort_reverse,
        )
        for m in matching_child_merkles:
            total_height = matches[m.digest][0]
            count = matches[m.digest][1]
            height = int(total_height / count)
            matches[m.digest] = ((total_height - height), count - 1)
            row = self._get_compare_table_row(m, match=True, height=height)
            compare_table.add_row(*row, key=str(m.path), height=height)
        for m in unmatched_child_merkles:
            if m.path.name in name_matches:
                row = self._get_compare_table_row(m, match=False, name_match=True)
                compare_table.add_row(*row, key=str(m.path), height=3)
        for m in unmatched_child_merkles:
            if m.path.name not in name_matches:
                row = self._get_compare_table_row(m, match=False, name_match=False)
                compare_table.add_row(*row, key=str(m.path), height=3)

    def _get_merkle_from_row_key(self, row_key: RowKey) -> Merkle:
        child_merkles = [m for m in self.submerkle.children.values()]
        filtered_child_merkles = [
            m for m in child_merkles if fuzzy_match(m.path.name, self.filter_by)
        ]
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
        ### Watch for synchronized scrolling ###
        def watch_scroll_y(old_scroll_y: float, new_scroll_y: float) -> None:
            logging.debug(
                f"watch_scroll_y in {self.id}: {old_scroll_y}, {new_scroll_y}"
            )
            # We only want to sync scroll when we are scrolling across matches
            # Once we reach unmatched merkles, we no longer want to sync scroll
            other = CompareWidget._get_other_compare_widget(self.id, self.parent)
            row_key = self._get_row_key_from_scroll_y(old_scroll_y)
            matches = self._get_matches()
            name_matches = self._get_name_matches()
            if other and row_key:
                m = self._get_merkle_from_row_key(row_key)
                if m.digest in matches or m.path.name in name_matches:
                    other.query_one(DataTable).scroll_to(
                        None, new_scroll_y, animate=False
                    )

        self.watch(self.query_one(DataTable), "scroll_y", watch_scroll_y, init=False)

        ### Watch for displaying tooltip ###
        dt = self.query_one(DataTable)

        def watch_hover_coordinate(old: Coordinate, new: Coordinate) -> None:
            try:
                dt.tooltip = dt.get_cell_at(new).plain.strip()
            except:
                pass

        self.watch(dt, "hover_coordinate", watch_hover_coordinate)

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
        MAX_DIGEST_WIDTH = 32
        # The math here is to prevent horizontal scrollbar from appearing
        # The vertical scrollbar may take width of 2
        # Besides that, we have 2 columns, and we have to split the rem width amongst them
        # Each column has a built-in padding of 1 on both sides (see cell_padding in DataTable docs)
        N_COLS = 2
        TOTAL_AVAILABLE_WIDTH = total_width - 2 - 2 * N_COLS
        if total_width != 0:
            if column_key == Columns.DIGEST.value.key:
                return min(MAX_DIGEST_WIDTH, TOTAL_AVAILABLE_WIDTH // 2)
            elif column_key == Columns.NAME.value.key:
                return TOTAL_AVAILABLE_WIDTH - min(
                    MAX_DIGEST_WIDTH, TOTAL_AVAILABLE_WIDTH // 2
                )
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
        self, m: Merkle, match: bool, name_match: bool = False, height: int = 3
    ) -> list[Text]:
        NCW = CompareWidget._get_column_width(
            self.size.width, column_key="NAME"
        )  # name column width
        DCW = CompareWidget._get_column_width(
            self.size.width, column_key="DIGEST"
        )  # digest column width
        # Variable Names Explained
        #   ns: name suffix
        #   ds: digest suffix
        #   ncp: name cell prefix
        #   ncs: name cell suffix
        #   dcp: digest cell prefix
        #   dcs: digest cell suffix
        if match:
            ns = " " * (NCW - len(m.path.name) - 3)
            ds = " " * (DCW - len(m.digest))
            ncp = (" " * (NCW) + "\n") * int((height - 1) / 2)
            ncs = ("\n" + " " * (NCW)) * (height - 1 - int((height - 1) / 2))
            dcp = (" " * (DCW) + "\n") * int((height - 1) / 2)
            dcs = ("\n" + " " * (DCW)) * (height - 1 - int((height - 1) / 2))
        elif name_match:
            ns = " " * (NCW - len(m.path.name) - 3)
            ds = " " * (DCW - len(m.digest))
            # for name match, we only need ns and ds
            NCW = 0
            DCW = 0
            ncp = (" " * (NCW) + "\n") * int((height - 1) / 2)
            ncs = ("\n" + " " * (NCW)) * (height - 1 - int((height - 1) / 2))
            dcp = (" " * (DCW) + "\n") * int((height - 1) / 2)
            dcs = ("\n" + " " * (DCW)) * (height - 1 - int((height - 1) / 2))
        else:
            # if neither (digest) match nor name match, we dont need any padding anywhere
            NCW = 0
            DCW = 0
            ns = " " * (NCW - len(m.path.name) - 3)
            ds = " " * (DCW - len(m.digest))
            ncp = (" " * (NCW) + "\n") * int((height - 1) / 2)
            ncs = ("\n" + " " * (NCW)) * (height - 1 - int((height - 1) / 2))
            dcp = (" " * (DCW) + "\n") * int((height - 1) / 2)
            dcs = ("\n" + " " * (DCW)) * (height - 1 - int((height - 1) / 2))
        row = [
            colorhash_styled_text(
                (ncp + file_prefix(m.type) + m.path.name + ns + ncs),
                m.digest,
            ),
            colorhash_styled_text(
                (dcp + m.digest + ds + dcs),
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

    def _get_name_matches(self) -> set[str]:
        other = CompareWidget._get_other_compare_widget(self.id, self.parent)
        if other:
            if self.loading or other.loading:
                return set()
            else:
                names_1 = [m.path.name for m in self.submerkle.children.values()]
                names_2 = [m.path.name for m in other.submerkle.children.values()]
                return set(names_1) & set(names_2)
        else:
            return set()
