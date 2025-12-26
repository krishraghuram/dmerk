from textual.geometry import Offset, Region
from textual.widgets import Input as TextualInput

from dmerk.tui.navigation import Direction, NavigationMixin


class Input(TextualInput):

    def edge_center(self, direction: Direction) -> Offset:
        x, y, width, height = self.region
        width = len(self.value)
        region = Region(x, y, width, height)
        return NavigationMixin.edge_center(region, direction)
