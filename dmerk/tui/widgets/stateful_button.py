from enum import Enum
from typing import Any

from textual.message import Message
from textual.widgets import Button


class StatefulButton(Button):

    class State(Enum):
        # Default state, button is not selected
        DEFAULT = 0
        # Button has been selected
        SELECTED = 1

    class StateChange(Message):
        def __init__(
            self,
            button: "StatefulButton",
            old_state: "StatefulButton.State",
            new_state: "StatefulButton.State",
        ):
            self.button = button
            self.old_state = old_state
            self.new_state = new_state
            super().__init__()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.active_effect_duration = 0
        self.state = StatefulButton.State.DEFAULT

    def reset_state(self) -> None:
        self.state = StatefulButton.State.DEFAULT
        self.remove_class("-primary")

    def set_state(self) -> None:
        if self.state == StatefulButton.State.DEFAULT:
            self.state = StatefulButton.State.SELECTED
            self.add_class("-primary")

    def press(self, human_press: bool = True) -> "StatefulButton":
        """Respond to a button press.

        Returns:
            The button instance.
        """
        if self.disabled or not self.display:
            return self
        old_state = self.state
        self.set_state()
        if human_press:
            self.post_message(StatefulButton.StateChange(self, old_state, self.state))
        return self

    def action_press(self, human_press: bool = True) -> None:
        """Activate a press of the button."""
        self.press(human_press)
