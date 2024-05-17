import logging
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Header,
    DataTable,
    RichLog,
    Button,
    TabbedContent,
    TabPane,
)
from textual.containers import Horizontal, Vertical
from textual.events import Mount, Ready
from textual import work
from dmerk.tui.widgets import FileManager, FavoritesSidebar, SidebarButton, FilePicker
import dmerk.generate as generate
import dmerk.constants as constants


# Taken from: https://github.com/Textualize/textual/discussions/2072#discussioncomment-5666856
class TextHandler(logging.Handler):
    """Class for  logging to a textual RichLog widget"""

    def __init__(self, richlog: RichLog):
        logging.Handler.__init__(self)
        self.text = richlog

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.text.write(msg)


class DmerkApp(App[None]):
    """An TUI for dmerk"""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    prev_tab = None

    def on_ready(self, event: Ready) -> None:
        root_logger = logging.getLogger()
        rich_log_handler = TextHandler(self.query_one(RichLog))
        rich_log_handler.setLevel(logging.INFO)
        rich_log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
            )
        )
        root_logger.handlers.clear()
        root_logger.addHandler(rich_log_handler)

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header()
        with TabbedContent(initial="generate"):
            with TabPane("Generate", id="generate"):  # First tab
                yield Vertical(
                    Horizontal(FavoritesSidebar(), FileManager(), id="files"),
                    Horizontal(
                        RichLog(),
                        Button("GENERATE", variant="primary", id="generate"),
                        id="generate",
                    ),
                )
            with TabPane("Compare", id="compare"):
                yield Vertical(
                    Horizontal(
                        FilePicker(id="filepicker-left"),
                        FilePicker(id="filepicker-right"),
                    ),
                )
                yield Button("COMPARE", "error", id="compare")
        yield Footer()

    async def on_tabbed_content_tab_activated(
        self, message: TabbedContent.TabActivated
    ) -> None:
        print(message)
        if self.prev_tab == "compare" and message.pane.id != "compare":
            await self.recompose()
            if message.pane.id:
                self.query_one(TabbedContent).active = message.pane.id
            else:
                raise ValueError(
                    f"Recomposed the UI, but couldn't set the tab because {message.pane.id=}"
                )
        self.prev_tab = message.pane.id

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        path = path.resolve()
        merkle = generate.generate(path)
        filename = constants.APP_STATE_PATH
        merkle.save(filename=filename)

    def on_button_pressed(self, message: Button.Pressed) -> None:
        highlighted_path = self.query_one(FileManager).highlighted_path
        if highlighted_path is not None:
            if highlighted_path.is_dir():
                self._main(highlighted_path)
            else:
                logging.warning("Please choose a directory")
        else:
            logging.warning("Please choose a path")

    def on_mount(self, event: Mount) -> None:
        self.query_one(FileManager).query_one(DataTable).focus()
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


def run() -> None:
    app.run()
