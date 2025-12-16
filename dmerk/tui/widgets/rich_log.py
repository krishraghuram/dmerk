from rich.console import RenderableType
from textual.widgets import RichLog as TextualRichLog

from dmerk.tui.navigation import Direction


class RichLog(TextualRichLog):
    def __init__(self, *args, **kwargs):
        kwargs["auto_scroll"] = False
        super().__init__(*args, **kwargs)

    def write(
        self,
        content: RenderableType | object,
        width: int | None = None,
        expand: bool = False,
        shrink: bool = True,
        scroll_end: bool | None = None,
        animate: bool = False,
    ) -> "RichLog":
        # If user has scrolled up to see older logs, then dont scroll to end when writing new log
        if scroll_end is None:
            scroll_end = self.is_vertical_scroll_end
        super().write(
            content,
            width=width,
            expand=expand,
            shrink=shrink,
            scroll_end=scroll_end,
            animate=animate,
        )
        return self

    def should_navigate(self, direction: Direction) -> bool:
        match direction:
            case Direction.UP:
                return self.scroll_y == 0
            case _:
                return True
