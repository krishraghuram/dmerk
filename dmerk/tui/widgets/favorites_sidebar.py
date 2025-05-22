from pathlib import Path
from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable
from textual.widgets._tabbed_content import ContentTabs
from textual.containers import Vertical
from textual.message import Message
from textual.binding import Binding
from textual.events import DescendantFocus, Focus
from .sidebar_button import SidebarButton


class FavoritesSidebar(Widget):
    focused_button = None

    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("tab", "cursor_right", "Tab", show=False),
    ]

    def action_cursor_up(self):
        if self.focused_button != self.query(SidebarButton)[0]:
            self.screen.focus_previous()
        else:
            self.screen.query_one(ContentTabs).focus()

    def action_cursor_down(self):
        if self.focused_button != self.query(SidebarButton)[-1]:
            self.screen.focus_next()

    def action_cursor_right(self):
        self.screen.query_one(DataTable).focus()

    def on_descendant_focus(self, event: DescendantFocus):
        self.focused_button = event.widget

    def on_focus(self, event: Focus):
        if self.focused_button is None:
            self.focused_button = self.query(SidebarButton)[0]
        self.focused_button.focus()

    def __init__(self, *args: Any, **kwargs: Any):
        self.can_focus = True
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Vertical(
            SidebarButton(Path("/"), "Computer"),
            SidebarButton(Path.home(), "Home"),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            SidebarButton(None, ""),
            # TODO: Add a mechanism to "add more" dynamically
            # TODO: And wrap this widget in a Scrollable
        )

    class PathSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def on_sidebar_button_state_change(self, event: SidebarButton.StateChange) -> None:
        # Reset all other buttons
        for button in self.query(SidebarButton):
            if button != event.button:
                button.reset_state()
        # If button is in selected state, emit PathSelected Message
        if event.button.path is not None:
            if event.button.state == SidebarButton.State.SELECTED:
                self.post_message(FavoritesSidebar.PathSelected(event.button.path))

    @staticmethod
    def _get_label_from_path(path: Path) -> str:
        if path == Path.home():
            return "Home"
        elif path == Path("/"):
            return "Computer"
        else:
            return path.name

    def path_selected(self, path: Path) -> None:
        # If there is a button in edit state, set it's label and path, and reset it
        for button in self.query(SidebarButton):
            if button.state == SidebarButton.State.EDIT:
                button.path = path
                button.label = FavoritesSidebar._get_label_from_path(path)
                button.reset_state()

    def path_change(self, path: Path) -> None:
        # If there is a button in selected state, and if its path is not matching the path argument, deselect the button,
        # If there is a button who's path is matching with the path argument, set it to selected state
        for button in self.query(SidebarButton):
            if button.state == SidebarButton.State.SELECTED:
                if button.path != path:
                    button.reset_state()
            elif button.state == SidebarButton.State.DEFAULT:
                if button.path == path:
                    button.action_press(human_press=False)
