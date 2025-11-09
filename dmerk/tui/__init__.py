import importlib.metadata
import logging
from enum import Enum
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Ready
from textual.logging import TextualHandler
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    RichLog,
    TabbedContent,
    TabPane,
)

import dmerk.constants as constants
import dmerk.generate as generate
from dmerk.tui.widgets import FavoritesSidebar, FileManager, FilePicker
from dmerk.tui.widgets.clearable_input import ClearableInput
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


class Tabs(Enum):
    Generate = "tab-generate"
    Compare = "tab-compare"


class DmerkApp(App[None]):
    """An TUI for dmerk"""

    TITLE = f"dmerk tui v{importlib.metadata.version('dmerk')}"

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    BUTTON_GENERATE = "button-generate"

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
        with TabbedContent(initial=Tabs.Generate.value):
            with TabPane(Tabs.Generate.name, id=Tabs.Generate.value):
                with Vertical():
                    with Horizontal(id="top"):
                        yield FavoritesSidebar()
                        yield FileManager()
                    with Horizontal(id="bottom"):
                        yield RichLog()
                        yield Button(
                            str.upper(Tabs.Generate.name),
                            variant="primary",
                            id=self.BUTTON_GENERATE,
                        )
            with TabPane(Tabs.Compare.name, id=Tabs.Compare.value):
                with Vertical():
                    yield ClearableInput(placeholder="Filter by...")
                    with Horizontal(id="horizontal"):
                        yield FilePicker(id="filepicker-left")
                        yield FilePicker(id="filepicker-right")
        yield Footer()

    @work(thread=True)
    async def _main(self, path: Path) -> None:
        path = path.resolve()
        merkle = generate.generate(path)
        filename = constants.APP_STATE_PATH
        merkle.save(filename=filename)

    def on_button_pressed(self, message: Button.Pressed) -> None:
        if message.button.id == self.BUTTON_GENERATE:
            highlighted_path = self.query_one(FileManager).highlighted_path
            if highlighted_path is not None:
                if highlighted_path.is_dir():
                    self._main(highlighted_path)
                else:
                    logging.warning("Please choose a directory")
            else:
                logging.warning("Please choose a path")

    def on_input_changed(self, message: Input.Changed) -> None:
        for file_picker in self.query(FilePicker):
            file_picker.filter_by = message.value
        for compare_widget in self.query(CompareWidget):
            compare_widget.filter_by = message.value

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

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
app.scroll_sensitivity_y = 1.0


def run() -> None:
    app.run()
