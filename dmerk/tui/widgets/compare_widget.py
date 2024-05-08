from pathlib import Path

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, DataTable
from textual.reactive import reactive
from textual.message import Message
from textual.events import Resize

import dmerk.constants as constants
from dmerk.merkle import Merkle

def file_prefix(path: Path) -> str:
    if path.is_symlink():
        return "🔗 "
    elif path.is_dir():
        return "📁 "
    elif path.is_file():
        return "📄 "
    else:
        return "⭐ "


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
        if path.is_file() and path.suffix==".dmerk":
            self.merkle = Merkle.load(path)
        else:
            raise ValueError(f"path {path} must be a dmerk file")

    prev_cell_key = None

    def __get_column_width(self) -> int | None:
        if self.size.width != 0:
            # the math is to prevent horizontal scrollbar from appearing
            return int((self.size.width - 2) / 2) - 2
        else:
            return None

    async def _refresh_table(self) -> None:
        compare_table = self.query_one(DataTable)
        compare_table.clear(columns=True)
        compare_table.add_column("\nName", key="NAME", width=self.__get_column_width())
        compare_table.add_column("\nDigest", key="DIGEST", width=self.__get_column_width())
        for m in self.merkle.children.values():
            compare_table.add_row(
                *[
                    "\n" + file_prefix(m.path) + m.path.name,
                    "\n" + m.digest,
                ],
                key=str(m.path),
                height=3,
            )



        # compare_table.add_row(*["\n.."], key="..", height=3)
        # compare_table = [p for p in self.path.iterdir() if p.exists()]
        # compare_table = sorted(files_list, key=lambda p: p.name)
        # for file in compare_table:
        #     compare_table.add_row(
        #         *["\n" + file_prefix(file) + file.name],
        #         key=str(file),
        #         height=3,
        #     )

    def compose(self) -> ComposeResult:
        # yield Button("Test", "error", id="compare")
        compare_table: DataTable[None] = DataTable(header_height=3)
        yield compare_table

    async def on_resize(self, event: Resize) -> None:
        await self._refresh_table()
