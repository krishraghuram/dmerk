from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, DataTable, Log, Button
from textual.containers import Horizontal, Vertical
from textual.events import Mount
from textual import work


from .widgets import FileManager, FavoritesSidebar, SidebarButton
from ..cli import _main
from .. import constants


class DmerkApp(App[None]):
    """An TUI for dmerk"""

    CSS_PATH = "styles.tcss"

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

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        args = [
            "generate",
            "-f",
            constants.APP_STATE_PATH,
            str(path),
        ]
        _main(args)

    def on_button_pressed(self, message: Button.Pressed) -> None:
        highlighted_path = self.query_one(FileManager).highlighted_path
        if highlighted_path is not None:
            if highlighted_path.is_dir():
                self._main(highlighted_path)
            else:
                print("Please choose a directory")
        else:
            print("Please choose a path")

    def on_mount(self, event: Mount) -> None:
        self.query_one(DataTable).focus()
        for button in self.query_one(FavoritesSidebar).query(SidebarButton):
            if str(button.label) == "Home":
                button.action_press()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_file_manager_path_selected(self, message: FileManager.PathSelected) -> None:
        self.query_one(FavoritesSidebar).path_selected(message.path)

    def on_file_manager_path_change(self, message: FileManager.PathChange) -> None:
        self.query_one(FavoritesSidebar).path_change(message.path)

    def on_favorites_sidebar_path_selected(
        self, message: FavoritesSidebar.PathSelected
    ) -> None:
        self.query_one(FileManager).path_selected(message.path)


app = DmerkApp()


if __name__ == "__main__":
    app.run()
