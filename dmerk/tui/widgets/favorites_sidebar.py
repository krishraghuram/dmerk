from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from dmerk.tui.widgets import StatefulButton


class FavoritesSidebar(Widget):

    BINDINGS = [
        ("r", "remove", "Remove"),
    ]

    def action_remove(self) -> None:
        if isinstance(self.app.focused, StatefulButton):
            idx_to_remove = None
            for idx, (p, b) in enumerate(self.items):
                if b == self.app.focused:
                    idx_to_remove = idx
                    break
            if idx_to_remove is not None:
                self.items.pop(idx_to_remove)
                # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
                self.mutate_reactive(FavoritesSidebar.items)

    MAX_BUTTONS = 6

    items: reactive[list[tuple[Path, StatefulButton]]] = reactive(list())

    @staticmethod
    def _label(path: Path) -> str:
        """
        For home and root, we would like to have special labels, for everything else, we use path.name
        """
        if path == Path.home():
            return "Home"
        elif path == Path("/"):
            return "Computer"
        else:
            return path.name

    def _path(self, button: StatefulButton) -> Path | None:
        """
        Return the path for the button
        """
        return next((p for p, b in self.items if b == button), None)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        paths = [Path("/"), Path.home()]
        # No need to trigger reactive here, because compose will run after init
        self.items.extend([(p, StatefulButton(self._label(p))) for p in paths])

    def compose(self) -> ComposeResult:
        with Vertical():
            for path, button in self.items:
                yield button

    def watch_items(self) -> None:
        # Remove buttons from DOM that are no longer in items
        buttons = [b for p, b in self.items]
        for b in self.query(StatefulButton):
            if b not in buttons:
                b.remove()
        # Mount buttons in items but not in DOM
        for p, b in self.items:
            if self not in b.ancestors:
                self.query_one(Vertical).mount(b)

    class PathSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def on_stateful_button_state_change(
        self, event: StatefulButton.StateChange
    ) -> None:
        # Reset all other buttons
        for button in self.query(StatefulButton):
            if button != event.button:
                button.reset_state()
        # If button is in selected state, emit PathSelected Message
        if event.button.state == StatefulButton.State.SELECTED:
            path = self._path(event.button)
            if path is not None:
                self.post_message(FavoritesSidebar.PathSelected(path))

    def can_add_favorite(self) -> bool:
        return len(self.items) < self.MAX_BUTTONS

    def add_favorite(self, path: Path) -> None:
        for button in self.query(StatefulButton):
            if path == self._path(button):
                # Selected path is already a favorite, dont add again
                return
        # Mount a new button
        if self.can_add_favorite():
            self.items.append((path, StatefulButton(self._label(path))))
            # Mutable reactives require manual trigger: https://textual.textualize.io/guide/reactivity/#mutable-reactives
            self.mutate_reactive(FavoritesSidebar.items)
        else:
            raise ValueError(
                f"Reached limit of {self.MAX_BUTTONS}, cant add more favorites"
            )

    def path_change(self, path: Path) -> None:
        # If there is a button in selected state, and if its path is not matching the path argument, deselect the button,
        # If there is a button who's path is matching with the path argument, set it to selected state
        for button in self.query(StatefulButton):
            if button.state == StatefulButton.State.SELECTED:
                if self._path(button) != path:
                    button.reset_state()
            elif button.state == StatefulButton.State.DEFAULT:
                if self._path(button) == path:
                    button.action_press(human_press=False)
