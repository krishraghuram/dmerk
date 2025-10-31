from functools import partial
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
    Leave,
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
    FOCUS_CLASS = "focus"
    CLICK_CLASS = "click"
    ID_LABEL_WIDGET = "label_widget"

    DEFAULT_CSS = """
            Horizontal {
            width: 100%;
            height: auto;
            Input {
                width: 100%;
                border: vkey $primary;
                color: $text-warning;
                background: $warning-muted; 
                &.empty {
                    background: $surface;
                }
            }
            #label_widget {
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
        self.label_widget = Widget(
            Label(label_text),
            classes=self.EMPTY_CLASS,
            id=self.ID_LABEL_WIDGET,
        )
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield self.input
            yield self.label_widget

    # When input is focused/blurred, set/remove "focus" class on Label Widget, so as to sync background-tint
    def on_descendant_focus(self, event: DescendantFocus):
        if event.widget == self.input:
            self.label_widget.add_class(self.FOCUS_CLASS)

    def on_descendant_blur(self, event: DescendantBlur):
        if event.widget == self.input:
            self.label_widget.remove_class(self.FOCUS_CLASS)

    # When input is empty/not, set/remove empty class
    def on_input_changed(self, message: Input.Changed) -> None:
        if message.value == "":
            self.input.add_class(self.EMPTY_CLASS)
            self.label_widget.add_class(self.EMPTY_CLASS)
        else:
            self.input.remove_class(self.EMPTY_CLASS)
            self.label_widget.remove_class(self.EMPTY_CLASS)

    # When label_widget (or the label inside) is clicked, add a click class so that we have visual feedback
    def on_mouse_down(self, event: MouseDown) -> None:
        event_widget = self.app.get_widget_at(event.screen_x, event.screen_y)[0]
        if event_widget and (self.label_widget in event_widget.ancestors_with_self):
            self.label_widget.add_class(self.CLICK_CLASS)

    def on_mouse_up(self, event: MouseUp) -> None:
        event_widget = self.app.get_widget_at(event.screen_x, event.screen_y)[0]
        if event_widget and (self.label_widget in event_widget.ancestors_with_self):
            self.label_widget.remove_class(self.CLICK_CLASS)

    def on_leave(self, event: Leave) -> None:
        event_widget = event.node
        if event_widget and (self.label_widget in event_widget.ancestors_with_self):
            self.label_widget.remove_class(self.CLICK_CLASS)

    def on_click(self, event: Click) -> None:
        if event.widget and (self.label_widget in event.widget.ancestors_with_self):
            self.input.clear()
