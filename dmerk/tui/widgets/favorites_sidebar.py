from pathlib import Path
from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Vertical
from textual.message import Message
from .sidebar_button import SidebarButton


class FavoritesSidebar(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Vertical(
            SidebarButton(Path("/"), "Computer"),
            SidebarButton(Path.home(), "Home"),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
        )

    class PathSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def on_sidebar_button_state_change(self, event: SidebarButton.StateChange):
        # Reset all other buttons
        for button in self.query(SidebarButton):
            if button != event.button:
                button.reset_state()
        # If button is in selected state, emit PathSelected Message
        if event.button.path is not None:
            if event.button.state == SidebarButton.State.SELECTED:
                self.post_message(FavoritesSidebar.PathSelected(event.button.path))

    @staticmethod
    def _get_label_from_path(path):
        if path == Path.home():
            return "Home"
        elif path == "/":
            return "Computer"
        else:
            return path.name

    def path_selected(self, path: Path):
        # If there is a button in edit state, set it's label and path, and reset it
        for button in self.query(SidebarButton):
            if button.state == SidebarButton.State.EDIT:
                button.path = path
                button.label = FavoritesSidebar._get_label_from_path(path)
                button.reset_state()

    def path_change(self, path: Path):
        # If there is a button in selected state, and if its path is not matching the path argument, deselect the button,
        # If there is a button who's path is matching with the path argument, set it to selected state
        for button in self.query(SidebarButton):
            if button.state == SidebarButton.State.SELECTED:
                if button.path != path:
                    button.reset_state()
            elif button.state == SidebarButton.State.DEFAULT:
                if button.path == path:
                    button.action_press(human_press=False)
