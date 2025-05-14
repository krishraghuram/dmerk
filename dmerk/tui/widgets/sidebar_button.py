from enum import Enum
from pathlib import Path
from typing import Any

from textual.widgets import Button
from textual.message import Message


class SidebarButton(Button):

    # Textual buttons have been changed
    # They cannot be pressed when already "active"
    # https://github.com/Textualize/textual/releases/tag/v0.66.0
    # https://github.com/Textualize/textual/pull/4621
    # So we are using custom style classes
    DEFAULT_CSS = """
    SidebarButton {
        &.-selected {
            background: $surface;
            border-bottom: tall $surface-lighten-1;
            border-top: tall $surface-darken-1;
            tint: $background 30%;
        }
        &.-edit {
            color: $button-color-foreground;
            background: $primary;
            border-top: tall $primary-lighten-3;
            border-bottom: tall $primary-darken-3;

            &:hover {
                background: $primary-darken-2;
                border-top: tall $primary;
            }

            &.-active {
                background: $primary;
                border-bottom: tall $primary-lighten-3;
                border-top: tall $primary-darken-3;
            }
        }
    }
    """

    class State(Enum):
        # Default state, button is not selected
        DEFAULT = 0
        # Button has been selected, and the corresponding path is displayed in FileManager
        SELECTED = 1
        # Button has been pressed once more after being selected, and is in edit mode.
        # Choosing a path in FileManager will update the button with the new path.
        EDIT = 2

    class StateChange(Message):
        def __init__(
            self,
            button: "SidebarButton",
            old_state: "SidebarButton.State",
            new_state: "SidebarButton.State",
        ):
            self.button = button
            self.old_state = old_state
            self.new_state = new_state
            super().__init__()

    def __init__(self, path: Path | None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.active_effect_duration = 0
        self.path: Path | None = path
        self.state = SidebarButton.State.DEFAULT

    def remove_classes(self) -> None:
        self.remove_class("-selected")
        self.remove_class("-edit")

    def reset_state(self) -> None:
        self.state = SidebarButton.State.DEFAULT
        self.remove_classes()

    def update_state(self) -> None:
        if self.state == SidebarButton.State.DEFAULT:
            self.state = SidebarButton.State.SELECTED
            self.remove_classes()
            self.add_class("-selected")
        elif self.state == SidebarButton.State.SELECTED:
            self.state = SidebarButton.State.EDIT
            self.remove_classes()
            self.add_class("-edit")
            # Additionally, remove label, path
            self.label = ""
            self.path = None
        elif self.state == SidebarButton.State.EDIT:
            self.reset_state()
        else:
            raise ValueError(f"state cannot be {self.state}")

    def press(self, human_press: bool = True) -> "SidebarButton":
        """Respond to a button press.

        Returns:
            The button instance."""
        if self.disabled or not self.display:
            return self
        # Manage the "active" effect:
        old_state = self.state
        self.update_state()
        # ...and let other components know that we've just been clicked:
        if human_press:
            self.post_message(SidebarButton.StateChange(self, old_state, self.state))
        return self

    def action_press(self, human_press: bool = True) -> None:
        """Activate a press of the button."""
        self.press(human_press)
