from itertools import zip_longest
from typing import cast
from textual.message import Message
from textual.widgets import Label
from textual.containers import Horizontal
from textual.widget import Widget
from textual.reactive import reactive
from textual.events import Key, Click
from rich.text import Text

from dataclasses import dataclass


class Crumb(Label):
    can_focus = True


class Breadcrumbs(Widget):
    @dataclass
    class Changed(Message):
        breadcrumbs: "Breadcrumbs"
        parts: list[str]

    ID_BREADCRUMBS = "breadcrumbs"

    parts: reactive[list[str] | None] = reactive(None, init=False)

    def __init__(self, initial: str | list[str]):
        super().__init__()
        if isinstance(initial, str):
            self.set_reactive(Breadcrumbs.parts, [initial])
        else:
            self.set_reactive(Breadcrumbs.parts, initial)

    def compose(self):
        with Horizontal(id=self.ID_BREADCRUMBS):
            for part in self.parts:
                yield Crumb(Text(f"{part}", style="bold"))

    def watch_parts(self):
        # Post message for parent to use
        self.post_message(Breadcrumbs.Changed(self, self.parts))
        # Update crumbs
        # Find mismatch point, and update only Crumbs after that
        # If Crumb instance exists, update them, instead of creating new ones
        # If not, say, because new_crumbs is longer, add new Crumb instances at the end as needed
        new_crumbs = [Crumb(Text(l, style="bold")) for l in self.parts]
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
            elif c and not n:
                c.remove()
            elif not c and n:
                self.query_one(Horizontal).mount(n)
            elif not c and not n:
                pass

    def _click_crumb(self, widget: Crumb):
        crumbs: list[Crumb] = []
        for c in self.query_one(Horizontal).children:
            if isinstance(c, Crumb) and isinstance(c.content, Text):
                crumbs.append(c)
        idx = crumbs.index(widget)
        self.parts = [cast(Text, l.content).plain for l in crumbs[: idx + 1]]
        # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
        self.mutate_reactive(Breadcrumbs.parts)

    def on_key(self, event: Key):
        if event.key == "enter":
            focused = self.app.focused
            if isinstance(focused, Crumb) and self in focused.ancestors:
                self._click_crumb(focused)

    def on_click(self, message: Click) -> None:
        if isinstance(message.widget, Crumb):
            self._click_crumb(message.widget)

    def update(self, parts):
        self.parts = parts
        # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
        self.mutate_reactive(Breadcrumbs.parts)
