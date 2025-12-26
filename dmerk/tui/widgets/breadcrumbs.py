from dataclasses import dataclass
from itertools import zip_longest
from typing import Any, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Click, Key
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class Crumb(Label):
    can_focus = True

    def __init__(self, part_idx: int, *args: Any, **kwargs: Any) -> None:
        self.part_idx = part_idx
        super().__init__(*args, **kwargs)


class Breadcrumbs(Widget):
    @dataclass
    class Changed(Message):
        breadcrumbs: "Breadcrumbs"
        parts: list[str]

    ID_BREADCRUMBS = "breadcrumbs"
    IDX_ELLIPSIS_CRUMB = -1

    parts: reactive[list[str]] = reactive(list(), init=False)

    def __init__(self, initial: str | list[str]):
        super().__init__()
        if isinstance(initial, str):
            self.set_reactive(Breadcrumbs.parts, [initial])
        else:
            self.set_reactive(Breadcrumbs.parts, initial)

    def compose(self) -> ComposeResult:
        with Horizontal(id=self.ID_BREADCRUMBS):
            for idx in range(len(self.parts)):
                yield self.new_crumb(idx)

    @staticmethod
    def crumbs_width(crumbs: list[Crumb]) -> int:
        # BUG: This probably wont work well for non-ascii stuff
        return sum([len(cast(Text, i.content).plain) for i in crumbs])

    def new_crumb(self, idx: int) -> Crumb:
        idx = idx % len(self.parts)
        return Crumb(idx, Text(self.parts[idx], style="bold"))

    @classmethod
    def ellipsis_crumb(cls) -> Crumb:
        return Crumb(cls.IDX_ELLIPSIS_CRUMB, Text("/...", style="bold"))

    def new_crumbs(self, show_ellipsis: bool = True) -> list[Crumb]:
        maxwidth = self.size.width
        new_crumbs = [self.new_crumb(idx) for idx in range(len(self.parts))]
        if show_ellipsis and self.crumbs_width(new_crumbs) > maxwidth:
            # Need to ellipsize middle crumbs
            # first_crumb, ellipsis_crumb and last_crumb always need to be included
            # Pick crumbs backwards, starting from last crumb, until we hit width limit
            first_crumb = self.new_crumb(0)
            ellipsis_crumb = self.ellipsis_crumb()
            last_crumb = self.new_crumb(-1)
            new_crumbs = [last_crumb]
            interior_indices = range(1, len(self.parts) - 1)
            for idx in reversed(interior_indices):
                next_crumb = self.new_crumb(idx)
                temp_new_crumbs = [first_crumb, ellipsis_crumb, next_crumb, *new_crumbs]
                if self.crumbs_width(temp_new_crumbs) < maxwidth:
                    new_crumbs.append(next_crumb)
                else:
                    break
            # Append the ellipsis_crumb and first_crumb at the end, and reverse to get in correct order
            new_crumbs.append(ellipsis_crumb)
            new_crumbs.append(first_crumb)
            new_crumbs = list(reversed(new_crumbs))
        return new_crumbs

    def _refresh(self, show_ellipsis: bool = True) -> None:
        # Update crumbs
        # Find mismatch point, and update only Crumbs after that
        # If Crumb instance exists, update them, instead of creating new ones
        # If not, say, because new_crumbs is longer, add new Crumb instances at the end as needed
        new_crumbs = self.new_crumbs(show_ellipsis)
        current_crumbs = list(self.query(Crumb))
        mismatch_idx = None
        for idx, (c, n) in enumerate(zip_longest(current_crumbs, new_crumbs)):
            if c is None or n is None or c.content != n.content:
                mismatch_idx = idx
                break
        else:
            return
        new_crumbs = new_crumbs[mismatch_idx:]
        current_crumbs = current_crumbs[mismatch_idx:]
        for c, n in zip_longest(current_crumbs, new_crumbs):
            if c and n:
                c.update(n.content)
                c.part_idx = n.part_idx
            elif c and not n:
                c.remove()
            elif not c and n:
                self.query_one(Horizontal).mount(n)
            elif not c and not n:
                pass
        # Need to call update_styles so that if the last-child had changed, the new last-child will get the appropriate style updates
        # This is relevant because we have a c.remove() above
        # Also, we need to call this after refresh, so that textual first updates the pseudo classes (such as last-child) on DOM nodes.
        self.app.call_after_refresh(self.app.update_styles, self)

    def watch_parts(self) -> None:
        self.post_message(Breadcrumbs.Changed(self, self.parts))
        self._refresh()

    def _click_crumb(self, widget: Widget | None) -> None:
        if not isinstance(widget, Crumb):
            raise ValueError("Illegal State!!!")
        try:
            idx = widget.part_idx
            if idx == self.IDX_ELLIPSIS_CRUMB:
                self._refresh(False)
            else:
                self.parts = self.parts[: idx + 1]
                # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
                self.mutate_reactive(Breadcrumbs.parts)
        except ValueError:
            raise

    def on_key(self, event: Key) -> None:
        if event.key == "enter":
            self._click_crumb(self.app.focused)

    def on_click(self, message: Click) -> None:
        self._click_crumb(message.widget)

    def update(self, parts: list[str]) -> None:
        self.parts = parts
        # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
        self.mutate_reactive(Breadcrumbs.parts)
