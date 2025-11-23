import functools
from itertools import zip_longest
import logging
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath
from typing import Callable, cast

from humanize import naturalsize
from more_itertools import partition
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.css.query import NoMatches
from textual.dom import DOMNode
from textual.events import Click, DescendantBlur, Resize, Key
from textual.geometry import Size
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label
from textual.widgets.data_table import RowKey
from textual.worker import Worker, WorkerState

from dmerk.merkle import Merkle
from dmerk.utils import PREFIX_SYMBOL_MERKLE, colorhash, fuzzy_match
from dmerk.tui.navigation import FocusPassthroughMixin, NavigationMixin


# Bug: https://trello.com/c/iizCU2oj
def colorhash_styled_text(text: str, digest: str) -> Text:
    return Text(str(text), style=f"bold grey11 on {colorhash(digest)}", no_wrap=True)


@dataclass
class Column:
    label: str
    key: str
    sort_key: Callable[[Merkle], str | int]
    sort_reverse: bool = False


class Columns(Enum):
    NAME = Column("Name", "NAME", lambda m: str.casefold(m.path.name))
    SIZE = Column("Size", "SIZE", lambda m: m.size, sort_reverse=True)
    DIGEST = Column("Digest", "DIGEST", lambda m: m.digest)


class CompareWidget(NavigationMixin, FocusPassthroughMixin, Widget):

    ID_BREADCRUMBS = "breadcrumbs"
    BUTTON_RESET_COMPARE = "button-reset-compare"
    DEFAULT_SORT_BY = None
    DEFAULT_SORT_REVERSE = False

    merkle_subpath: reactive[PurePath | None] = reactive(None)
    prev_cell_key = None
    filter_by = reactive("")
    sort_by: Reactive[None | str] = reactive(DEFAULT_SORT_BY)
    sort_reverse: Reactive[bool] = reactive(DEFAULT_SORT_REVERSE)
    prev_screen_size: Reactive[Size | None] = reactive(None)

    @property
    def matches_sort_key(self) -> Callable[[Merkle], str | int]:
        # By default, we want to sort digest-matches by digest, so that matching items show up side-by-side
        if self.sort_by:
            return Columns[self.sort_by].value.sort_key
        else:
            return lambda m: m.digest

    @property
    def unmatched_sort_key(self) -> Callable[[Merkle], str | int]:
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
        filter_by: str | None = None,
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
        if filter_by:
            self.filter_by = filter_by

    async def _reset_to_filepicker(self) -> None:
        from dmerk.tui.widgets.file_picker import FilePicker

        await cast(Widget, self.parent).mount(
            FilePicker(filter_by=self.filter_by), after=self
        )
        await self.remove()
        self.call_after_refresh(
            cast(Widget, self.parent).query_one(FilePicker).query_one(DataTable).focus
        )

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
            # TODO: Ideally we should have this check,
            # adding it makes it so that,
            # in some race conditions,
            # the focus is lost (no widget is focused)
            # if self is self.app.focused:
            self.call_after_refresh(self.query_one(DataTable).focus)
            await self._refresh()
        elif attempt < MAX_ATTEMPTS:
            self.call_after_refresh(lambda: self._refresh_when_ready(attempt + 1))
        else:
            logging.error(f"Widget {self.id} failed to initialize")

    def compose(self) -> ComposeResult:
        self.prev_screen_size = self.screen.size
        if not self.loading:
            compare_table: DataTable[None] = DataTable(header_height=3)
            with Vertical():
                with Horizontal(id=self.ID_BREADCRUMBS):
                    yield Label(Text(f"{self.merkle.path}", style="bold"))
                yield compare_table
                yield Button("RESET", "primary", id=self.BUTTON_RESET_COMPARE)

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
        Handle column header clicks with three-state sorting cycle.

        Clicking the same column cycles through:
        1. Default sort direction for that column
        2. Reversed sort direction
        3. Reset to default table sorting

        Clicking a different column starts a new cycle from step 1.
        """
        if self.sort_by != message.column_key.value:
            if message.column_key.value is None:
                raise ValueError("Illegal State")
            self.sort_by = message.column_key.value
            self.sort_reverse = Columns[self.sort_by].value.sort_reverse
        else:
            if self.sort_by is None:
                raise ValueError("Illegal State")
            if self.sort_reverse is Columns[self.sort_by].value.sort_reverse:
                self.sort_reverse = not Columns[self.sort_by].value.sort_reverse
            else:
                self.sort_by = self.DEFAULT_SORT_BY
                self.sort_reverse = self.DEFAULT_SORT_REVERSE

    def _click_label(self, widget: Label):
        labels: list[Label] = []
        for c in self.query_one(Horizontal).children:
            if isinstance(c, Label) and isinstance(c.content, Text):
                labels.append(c)
        idx = labels.index(widget)
        merkle_subpath_parts = [cast(Text, l.content).plain for l in labels[: idx + 1]]
        self.merkle_subpath = PurePath("".join(merkle_subpath_parts))

    def on_key(self, event: Key):
        if event.key == "enter":
            focused = self.app.focused
            if isinstance(focused, Label) and self in focused.ancestors:
                self._click_label(focused)

    def on_click(self, message: Click) -> None:
        if isinstance(message.widget, Label):
            self._click_label(message.widget)

    def _sync_sort_fields(self) -> None:
        other = CompareWidget._get_other_compare_widget(self)
        if other:
            other.sort_by = self.sort_by
            other.sort_reverse = self.sort_reverse

    async def _refresh(self) -> None:
        if not self.loading:
            await self._refresh_label()
            await self._refresh_table(force=True)
            other = CompareWidget._get_other_compare_widget(self)
            if other:
                if not other.loading:
                    await other._refresh_label()
                    await other._refresh_table()

    async def _refresh_label(self) -> None:
        label_parts = [str(self.merkle.path)]
        label_parts = label_parts + [
            f"/{p}" for p in self.submerkle.path.relative_to(self.merkle.path).parts
        ]
        new_labels = [Label(Text(l, style="bold")) for l in label_parts]
        breadcrumbs_container = self.query_one(f"#{self.ID_BREADCRUMBS}")
        existing_labels = list(breadcrumbs_container.query(Label))
        mismatch_idx = None
        for idx, (existing_label, new_label) in enumerate(
            zip_longest(existing_labels, new_labels, fillvalue=None)
        ):
            if (
                existing_label is None
                or new_label is None
                or existing_label.content != new_label.content
            ):
                mismatch_idx = idx
            if mismatch_idx and idx >= mismatch_idx:
                if existing_label and new_label:
                    existing_label.update(new_label.content)
                elif existing_label and not new_label:
                    existing_label.remove()
                elif not existing_label and new_label:
                    breadcrumbs_container.mount(new_label)
                elif not existing_label and not new_label:
                    pass

    def _get_header_label(self, column: Column) -> str:
        if self.sort_by == column.key:
            return "\n" + column.label + (" ▾" if self.sort_reverse else " ▴")
        else:
            return "\n" + column.label

    async def _refresh_table(self, force: bool = False) -> None:
        digest_matches = self.digest_matches
        name_matches = self.name_matches
        compare_table = self.query_one(DataTable)
        # Check if we can do "partial refresh"
        if not force and len(digest_matches) == 0 and len(name_matches) == 0:
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
        child_merkles = (m for m in self.submerkle.children.values())
        filtered_child_merkles = (
            m for m in child_merkles if fuzzy_match(m.path.name, self.filter_by)
        )
        unmatched, matching = partition(
            lambda m: m.digest in digest_matches, filtered_child_merkles
        )
        matching_child_merkles = sorted(
            matching, key=self.matches_sort_key, reverse=self.sort_reverse
        )
        unmatched_child_merkles = sorted(
            unmatched, key=self.unmatched_sort_key, reverse=self.sort_reverse
        )
        digest_matches = (
            digest_matches.copy()
        )  # So that we dont mutate self.digest_matches (which is cached) and cause bugs
        for m in matching_child_merkles:
            total_height = digest_matches[m.digest][0]
            count = digest_matches[m.digest][1]
            height = int(total_height / count)
            digest_matches[m.digest] = ((total_height - height), count - 1)
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
        child_merkles = (m for m in self.submerkle.children.values())
        filtered_child_merkles = (
            m for m in child_merkles if fuzzy_match(m.path.name, self.filter_by)
        )
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
            other = CompareWidget._get_other_compare_widget(self)
            row_key = self._get_row_key_from_scroll_y(old_scroll_y)
            if other and row_key:
                m = self._get_merkle_from_row_key(row_key)
                if m.digest in self.digest_matches or m.path.name in self.name_matches:
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

    def _get_other_compare_widget(self) -> "CompareWidget|None":
        parent = self.parent
        if parent is not None:
            if parent.id == "left":
                other_parent_id = "right"
            elif parent.id == "right":
                other_parent_id = "left"
            else:
                raise ValueError(f"Unexpected parent id {parent.id}")
        else:
            raise ValueError("self.parent is None!!!")
        grandparent = parent.parent
        if grandparent is not None:
            try:
                other_parent = grandparent.query_one(f"#{other_parent_id}")
                return other_parent.query_one(CompareWidget)
            except NoMatches:
                logging.debug(f"No Matches for {other_parent_id}")
                return None
        else:
            raise ValueError("parent.parent is None!!!")

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _get_column_width(total_width: int, column_key: str) -> int:
        MAX_DIGEST_WIDTH = 8
        SIZE_WIDTH = 10
        # The math here is to prevent horizontal scrollbar from appearing
        # The vertical scrollbar may take width of 2
        # Besides that, we have 2 columns, and we have to split the rem width amongst them
        # Each column has a built-in padding of 1 on both sides (see cell_padding in DataTable docs)
        N_COLS = len(Columns)
        TOTAL_AVAILABLE_WIDTH = total_width - 2 - 2 * N_COLS
        TOTAL_AVAILABLE_WIDTH = TOTAL_AVAILABLE_WIDTH - SIZE_WIDTH
        if total_width != 0:
            if column_key == Columns.SIZE.value.key:
                return SIZE_WIDTH
            elif column_key == Columns.DIGEST.value.key:
                return min(MAX_DIGEST_WIDTH, TOTAL_AVAILABLE_WIDTH // 2)
            elif column_key == Columns.NAME.value.key:
                return TOTAL_AVAILABLE_WIDTH - min(
                    MAX_DIGEST_WIDTH, TOTAL_AVAILABLE_WIDTH // 2
                )
            else:
                raise ValueError(f"Unknown {column_key=}")
        else:
            return 0

    # Note that we CANNOT make this a staticmethod, since we use virtual/dummy parent merkle above (in worker _main)
    # The virtual/dummy parent merkle has identical hash values regardless of which merkle tree is loaded
    # And so, if this was a staticmethod, we'd have cache collisions (i.e., we'd incorrectly return the wrong merkle)
    @functools.lru_cache(maxsize=16)
    def _submerkle(self, merkle: Merkle, subpath: PurePath | None) -> Merkle:
        if subpath and subpath != merkle.path:
            return merkle.traverse(subpath)
        else:
            return merkle

    @property
    def submerkle(self) -> Merkle:
        return self._submerkle(self.merkle, self.merkle_subpath)

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _column_prefix(column_width: int, height: int) -> str:
        return (" " * (column_width) + "\n") * int((height - 1) / 2)

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _column_suffix(column_width: int, height: int) -> str:
        return ("\n" + " " * (column_width)) * (height - 1 - int((height - 1) / 2))

    def _get_compare_table_row(
        self, m: Merkle, match: bool, name_match: bool = False, height: int = 3
    ) -> list[Text]:
        """Generate a formatted table row for a Merkle node in the comparison view.

        - Digest Matches: Full cell background (horizontal + vertical padding)
        - Name matches: Horizontal line background (horizontal padding only)
        - No match: No background padding (just text gets colored)
        """
        NCW = CompareWidget._get_column_width(
            self.size.width, column_key="NAME"
        )  # name column width
        SCW = CompareWidget._get_column_width(
            self.size.width, column_key="SIZE"
        )  # size column width
        DCW = CompareWidget._get_column_width(
            self.size.width, column_key="DIGEST"
        )  # digest column width
        # Variable Names Explained
        #   ns, ds, ss: name, digest, size "suffix" - the amount of padding after the cell value on the same line
        #   ncp, dcp, scp: name, digest, size "cell prefix" - the amount of multiline-padding before cell value
        #   ncs, dcs, scs: name, digest, size "cell suffix" - the amount of multiline-padding after cell value
        ns = " " * (NCW - len(m.path.name) - 3)
        ds = " " * (DCW - len(m.digest))
        ss = " " * (SCW - len(naturalsize(m.size)))
        if name_match:
            # for name match, we only need "suffix", dont need "cell prefix" or "cell suffix"
            NCW = DCW = SCW = 0
        if not match and not name_match:
            # if neither (digest) match nor name match, we dont need any padding anywhere
            ns = ds = ss = ""
            NCW = DCW = SCW = 0
        ncp = self._column_prefix(NCW, height)
        dcp = self._column_prefix(DCW, height)
        scp = self._column_prefix(SCW, height)
        ncs = self._column_suffix(NCW, height)
        dcs = self._column_suffix(DCW, height)
        scs = self._column_suffix(SCW, height)
        # Build cells and return row
        prefix_symbol = PREFIX_SYMBOL_MERKLE.get(m.type, PREFIX_SYMBOL_MERKLE.get(None))
        name_cell = colorhash_styled_text(
            f"{ncp}{prefix_symbol}{m.path.name}{ns}{ncs}", m.digest
        )
        size_cell = colorhash_styled_text(
            f"{scp}{naturalsize(m.size)}{ss}{scs}", m.digest
        )
        digest_cell = colorhash_styled_text(f"{dcp}{m.digest}{ds}{dcs}", m.digest)
        return [name_cell, size_cell, digest_cell]

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def _get_digest_matches(
        self_submerkle: Merkle, other_submerkle: Merkle
    ) -> dict[str, tuple[int, int]]:
        # Note: Cant use generators here since we need digest_1 and digest_2 multiple times
        digests_1 = [m.digest for m in self_submerkle.children.values()]
        digests_2 = [m.digest for m in other_submerkle.children.values()]
        intersection = set(digests_1) & set(digests_2)
        counter_1 = Counter(digests_1)
        counter_2 = Counter(digests_2)
        digest_matches = {
            i: (3 * max(counter_1[i], counter_2[i]), counter_1[i]) for i in intersection
        }
        return digest_matches

    @property
    def digest_matches(self) -> dict[str, tuple[int, int]]:
        other = CompareWidget._get_other_compare_widget(self)
        if other:
            if self.loading or other.loading:
                return dict()
            else:
                return self._get_digest_matches(self.submerkle, other.submerkle)
        else:
            return dict()

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def _get_name_matches(self_submerkle: Merkle, other_submerkle: Merkle) -> set[str]:
        digest_matches = CompareWidget._get_digest_matches(
            self_submerkle, other_submerkle
        )
        names_1 = (
            m.path.name
            for m in self_submerkle.children.values()
            if m.digest not in digest_matches
        )
        names_2 = (
            m.path.name
            for m in other_submerkle.children.values()
            if m.digest not in digest_matches
        )
        return set(names_1) & set(names_2)

    @property
    def name_matches(self) -> set[str]:
        other = CompareWidget._get_other_compare_widget(self)
        if other:
            if self.loading or other.loading:
                return set()
            else:
                return self._get_name_matches(self.submerkle, other.submerkle)
        else:
            return set()

    # Taken from textual's Widget, and removed loading from the check,
    # because we want CompareWidget to be focusable even when loading
    # https://github.com/Textualize/textual/blob/e66c098588360515864ce88982de494c64d2c097/src/textual/widget.py#L2310
    @property
    def focusable(self) -> bool:
        """Can this widget currently be focused?"""
        return (
            self.allow_focus() and self.visible and not self._self_or_ancestors_disabled
        )
