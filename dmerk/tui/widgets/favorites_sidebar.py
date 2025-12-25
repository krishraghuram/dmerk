from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget

from dmerk.tui.widgets import StatefulButton


class FavoritesSidebar(Widget):
    N_BUTTONS = 6

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.paths = [Path("/"), Path.home()]

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

        Find the index of the button in the DOM tree, and return the path for that index, else return None
        """
        idx = self.query_one(Vertical).children.index(button)
        if idx < len(self.paths):
            return self.paths[idx]
        return None

    def compose(self) -> ComposeResult:
        with Vertical():
            for path in self.paths:
                yield StatefulButton(self._label(path))
            for i in range(self.N_BUTTONS - len(self.paths)):
                yield StatefulButton("")

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

    def path_selected(self, path: Path) -> None:
        for button in self.query(StatefulButton):
            if path == self._path(button):
                # Selected path is already a favorite, dont add again
                return
            if button.label == "":
                # Found a empty button, can add path as favorite
                self.paths.append(path)
                button.label = self._label(path)
                return
        # TODO:
        # This is not done yet, because this is called when FileManager.PathSelected message is emitted,
        # which happens every time user navigates in FileManager.
        # So this will mean that we'll quickly fillup all StatefulButton as user navigates the FileManager.
        # Instead, we want to change this to only be called when user wants to "add a new favorite sidebar item".
        # For that, we'll have to use something like a keybinding for the user to enter "set favorite mode" in FileManager.

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
