from widgets import FileManager, FavoritesSidebar, SidebarButton

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, DataTable, Log, Button
from textual.containers import Horizontal, Vertical
from textual.events import Mount


class DmerkApp(App):
    """An TUI for dmerk"""

    CSS_PATH = "dmerk_tui.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header()
        yield Vertical(
            Horizontal(FavoritesSidebar(), FileManager(), id="files"),
            Horizontal(
                Log(),
                Button("GENERATE", variant="primary", id="generate"),
                id="generate",
            ),
        )
        yield Footer()

    def on_mount(self, event: Mount):
        self.query_one(DataTable).focus()
        for button in self.query_one(FavoritesSidebar).query(SidebarButton):
            if str(button.label) == "Home":
                button.action_press()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_file_manager_path_selected(self, message: FileManager.PathSelected):
        self.query_one(FavoritesSidebar).path_selected(message.path)

    def on_file_manager_path_change(self, message: FileManager.PathChange):
        self.query_one(FavoritesSidebar).path_change(message.path)

    def on_favorites_sidebar_path_selected(
        self, message: FavoritesSidebar.PathSelected
    ):
        self.query_one(FileManager).path_selected(message.path)


if __name__ == "__main__":
    app = DmerkApp()
    app.run()
