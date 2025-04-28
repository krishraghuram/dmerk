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
import sys

from textual._context import active_app

from dmerk.tui.widgets.compare_widget import CompareWidget


# Taken from: https://github.com/Textualize/textual/discussions/2072#discussioncomment-5666856
class TextHandler(logging.Handler):
    """Class for  logging to a textual RichLog widget"""

    def __init__(self, richlog: RichLog):
        logging.Handler.__init__(self)
        self.text = richlog

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.text.write(msg)


# Monkey Patching from textual source
# https://github.com/Textualize/textual/blob/8bfa533fe90a1c4d248b4fdeb127d82c1781f003/src/textual/logging.py#L15
class TextualHandler(logging.Handler):
    """A Logging handler for Textual apps."""

    def __init__(self, stderr: bool = True, stdout: bool = False) -> None:
        """Initialize a Textual logging handler.

        Args:
            stderr: Log to stderr when there is no active app.
            stdout: Log to stdout when there is not active app.
        """
        super().__init__()
        self._stderr = stderr
        self._stdout = stdout

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        message = self.format(record)
        try:
            app = active_app.get()
        except LookupError:
            if self._stderr:
                print(message, file=sys.stderr)
            elif self._stdout:
                print(message, file=sys.stdout)
        else:
            app.log.debug(message)


class DmerkApp(App[None]):
    """An TUI for dmerk"""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def on_ready(self, event: Ready) -> None:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        rich_log_handler = TextHandler(self.query_one(RichLog))
        rich_log_handler.setLevel(logging.INFO)
        rich_log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
            )
        )
        root_logger.handlers.clear()
        root_logger.addHandler(rich_log_handler)
        root_logger.addHandler(TextualHandler())

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
                yield Button("RESET", "primary", id="reset-compare")
        yield Footer()

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        path = path.resolve()
        merkle = generate.generate(path)
        filename = constants.APP_STATE_PATH
        merkle.save(filename=filename)

    def on_button_pressed(self, message: Button.Pressed) -> None:
        if message.button.id == "generate":
            highlighted_path = self.query_one(FileManager).highlighted_path
            if highlighted_path is not None:
                if highlighted_path.is_dir():
                    self._main(highlighted_path)
                else:
                    logging.warning("Please choose a directory")
            else:
                logging.warning("Please choose a path")
        elif message.button.id == "reset-compare":
            for compare_widget in self.query(CompareWidget):
                compare_widget.reset_to_filepicker()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark  # type: ignore

    def on_file_manager_path_selected(self, message: FileManager.PathSelected) -> None:
        logging.debug(message)
        self.query_one(FavoritesSidebar).path_selected(message.path)

    def on_file_manager_path_change(self, message: FileManager.PathChange) -> None:
        logging.debug(message)
        self.query_one(FavoritesSidebar).path_change(message.path)

    def on_favorites_sidebar_path_selected(
        self, message: FavoritesSidebar.PathSelected
    ) -> None:
        logging.debug(message)
        self.query_one(FileManager).path_selected(message.path)


app = DmerkApp()


def run() -> None:
    app.run()
