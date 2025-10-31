from typing_extensions import Literal
from textual.widget import Widget
from textual.widgets import Input, Label
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import (
    Ready,
    Click,
    DescendantFocus,
    DescendantBlur,
    MouseDown,
    MouseUp,
)
from textual.widgets._input import InputType, InputValidationOn
from textual.suggester import Suggester
from textual.validation import Validator
from typing import Iterable
from rich.highlighter import Highlighter
from rich.console import RenderableType


class ClearableInput(Widget):

    LabelText = Literal["⌫", "🗑️", "✖️"]

    EMPTY_CLASS = "empty"

    DEFAULT_CSS = """
    Horizontal {
        width: 100%;
        height: auto;
        Input {
            border: vkey $primary;
            color: $text-warning;
            background: $warning-muted; 
            &.empty {
                background: $surface;
            }
        }
        Widget {
            height: 3;
            width: 5;
            position: relative;
            offset: -7 0;
            overlay: screen;
            align: center middle;
            background: $warning-muted;
            &.click {
                border: round $primary;
            }
            &.empty {
                background: $surface;
            }
            &.focus {
                background-tint: $foreground 5%;
            }
            Label {
                color: $primary;
                margin-right: 1;
            }
        }
    }
    """

    def __init__(
        self,
        *,
        placeholder: str = "",
        label_text: LabelText = "⌫",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        value: str | None = None,
        highlighter: Highlighter | None = None,
        password: bool = False,
        restrict: str | None = None,
        type: InputType = "text",
        max_length: int = 0,
        suggester: Suggester | None = None,
        validators: Validator | Iterable[Validator] | None = None,
        validate_on: Iterable[InputValidationOn] | None = None,
        valid_empty: bool = False,
        select_on_focus: bool = True,
        tooltip: RenderableType | None = None,
        compact: bool = False,
    ):
        self.input = Input(
            value=value,
            placeholder=placeholder,
            highlighter=highlighter,
            password=password,
            restrict=restrict,
            type=type,
            max_length=max_length,
            suggester=suggester,
            validators=validators,
            validate_on=validate_on,
            valid_empty=valid_empty,
            select_on_focus=select_on_focus,
            tooltip=tooltip,
            compact=compact,
            classes=self.EMPTY_CLASS,
        )
        self.label_widget = Widget(Label(label_text), classes=self.EMPTY_CLASS)
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield self.input
            yield self.label_widget

    # When input is focused/blurred, set/remove "focus" class on Label Widget, so as to sync background-tint
    def on_descendant_focus(self, event: DescendantFocus):
        if event.widget == self.query_one(Input):
            self.query_one(Widget).add_class("focus")

    def on_descendant_blur(self, event: DescendantBlur):
        if event.widget == self.query_one(Input):
            self.query_one(Widget).remove_class("focus")

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.value == "":
            message.input.add_class("empty")
            self.query_one(Widget).add_class("empty")
        else:
            message.input.remove_class("empty")
            self.query_one(Widget).remove_class("empty")
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

    def on_mouse_up(self, event: MouseUp) -> None:
        widget_at_event = self.get_widget_at(event.screen_x, event.screen_y)[0]
        erase_label_widget = self.query_one(
            f"#{Tabs.Compare.value} #top #{self.ERASE_LABEL_WIDGET}", Widget
        )
        if widget_at_event and (
            erase_label_widget in widget_at_event.ancestors_with_self
        ):
            erase_label_widget.remove_class("click")

    def on_click(self, event: Click) -> None:
        erase_label_widget = self.query_one(
            f"#{Tabs.Compare.value} #top #{self.ERASE_LABEL_WIDGET}", Widget
        )
        if event.widget and (erase_label_widget in event.widget.ancestors_with_self):
            self.query_one(Input).clear()
