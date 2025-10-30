from enum import Enum
from functools import partial
import logging
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Header,
    RichLog,
    Button,
    TabbedContent,
    TabPane,
    Input,
    Label,
)
from textual.widget import Widget
from textual.containers import Horizontal, Vertical
from textual.events import (
    Ready,
    Click,
    DescendantFocus,
    DescendantBlur,
    MouseDown,
)
from textual.logging import TextualHandler
from textual import work
from dmerk.tui.widgets import FileManager, FavoritesSidebar, FilePicker
import dmerk.generate as generate
import dmerk.constants as constants

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

    TITLE = "dmerk TUI"

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    BUTTON_GENERATE = "button-generate"
    ERASE_LABEL_WIDGET = "erase"

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
        with TabbedContent(initial=Tabs.Compare.value):
            with TabPane(Tabs.Generate.name, id=Tabs.Generate.value):
                yield Vertical(
                    Horizontal(FavoritesSidebar(), FileManager(), id="top"),
                    Horizontal(
                        RichLog(),
                        Button(
                            str.upper(Tabs.Generate.name),
                            variant="primary",
                            id=self.BUTTON_GENERATE,
                        ),
                        id="bottom",
                    ),
                )
            with TabPane(Tabs.Compare.name, id=Tabs.Compare.value):
                yield Vertical(
                    Horizontal(
                        Input(classes="empty", placeholder="Filter by..."),
                        Widget(Label("⌫"), classes="empty", id=self.ERASE_LABEL_WIDGET),
                        id="top",
                    ),
                    Horizontal(
                        FilePicker(id="filepicker-left"),
                        FilePicker(id="filepicker-right"),
                        id="bottom",
                    ),
                )
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

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        if event.widget == self.query_one(Input):
            self.query_one(f"#{self.ERASE_LABEL_WIDGET}", Widget).add_class("focus")

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        if event.widget == self.query_one(Input):
            self.query_one(f"#{self.ERASE_LABEL_WIDGET}", Widget).remove_class("focus")

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.value == "":
            message.input.add_class("empty")
            self.query_one(f"#{self.ERASE_LABEL_WIDGET}", Widget).add_class("empty")
        else:
            message.input.remove_class("empty")
            self.query_one(f"#{self.ERASE_LABEL_WIDGET}", Widget).remove_class("empty")
        for file_picker in self.query(FilePicker):
            file_picker.filter_by = message.value
        for compare_widget in self.query(CompareWidget):
            compare_widget.filter_by = message.value

    def on_mouse_down(self, event: MouseDown) -> None:
        widget_at_event = self.get_widget_at(event.screen_x, event.screen_y)[0]
        erase_label_widget = self.query_one(
            f"#{Tabs.Compare.value} #top #{self.ERASE_LABEL_WIDGET}", Widget
        )
        if widget_at_event and (
            erase_label_widget in widget_at_event.ancestors_with_self
        ):
            erase_label_widget.add_class("click")
            self.set_timer(0.2, partial(erase_label_widget.remove_class, "click"))
            # erase_label_widget.add_class("click")

    # def on_mouse_up(self, event: MouseUp) -> None:
    #     widget_at_event = self.get_widget_at(event.screen_x, event.screen_y)[0]
    #     erase_label_widget = self.query_one(
    #         f"#{Tabs.Compare.value} #top #{self.ERASE_LABEL_WIDGET}", Widget
    #     )
    #     if widget_at_event and (
    #         erase_label_widget in widget_at_event.ancestors_with_self
    #     ):
    #         erase_label_widget.remove_class("click")

    def on_click(self, event: Click) -> None:
        erase_label_widget = self.query_one(
            f"#{Tabs.Compare.value} #top #{self.ERASE_LABEL_WIDGET}", Widget
        )
        if event.widget and (erase_label_widget in event.widget.ancestors_with_self):
            self.query_one(Input).clear()

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
