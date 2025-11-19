from typing import Callable, cast
from enum import Enum

from textual.widget import Widget
from textual.widgets import TabbedContent, DataTable
from textual.widgets._tabbed_content import ContentTab, ContentTabs
from textual.app import App
from textual.events import Key


class Direction(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"

    @classmethod
    def from_key(cls, key: str) -> "Direction":
        if key == "up":
            return cls.UP
        elif key == "down":
            return cls.DOWN
        elif key == "left":
            return cls.LEFT
        elif key == "right":
            return cls.RIGHT
        else:
            raise ValueError(f"Unexpected value {key=} in Direction.from_key")


DomQuery = str
Source = DomQuery | Widget
NavCallable = Callable[[Widget, Direction], None]
Target = DomQuery | Widget | Callable[[Widget, Direction], None]
DirectionTargetMap = dict[Direction, Target]
NavSchema = dict[Source, DirectionTargetMap]


class NavigationSchema:
    def __init__(self, app: App):
        self.app = app

        self._schema: NavSchema = {
            "FileManager ClearableInput Input": {
                Direction.UP: "ContentTabs",
                Direction.LEFT: "SidebarButton",
                Direction.DOWN: "FileManager DataTable",
            },
        }

        # FileManager
        def filemanager(w: Widget, d: Direction):
            match d:
                case Direction.LEFT:
                    if cast(DataTable, w).cursor_column == 0:
                        w.app.query("SidebarButton").focus()
                case Direction.UP:
                    if cast(DataTable, w).cursor_row == 0:
                        w.app.query("FileManager ClearableInput Input").focus()

        self._schema.update(
            {
                "FileManager DataTable": {
                    Direction.LEFT: filemanager,
                    Direction.UP: filemanager,
                }
            }
        )

        # Tabs
        def tab_down(w: Widget, d: Direction):
            from dmerk.tui.app import Tabs

            w = cast(TabbedContent, w.parent)
            if w.active == Tabs.Generate.value:
                w.query_one("FavoritesSidebar SidebarButton").focus()
            elif w.active == Tabs.Compare.value:
                w.query_one("ClearableInput Input").focus()

        self._schema.update({"ContentTabs": {Direction.DOWN: tab_down}})

        # SidebarButton
        def up(w: Widget, d: Direction):
            if not w.first_child:
                w.screen.focus_previous()
            elif w.first_child:
                w.app.query_one(ContentTabs).focus()

        def down(w: Widget, d: Direction):
            if not w.last_child:
                w.screen.focus_next()

        self._schema.update(
            {
                w: {
                    Direction.UP: up,
                    Direction.DOWN: down,
                    Direction.RIGHT: "FileManager ClearableInput Input",
                }
                for w in self.app.query("SidebarButton")
            }
        )

    def navigate(self, from_widget: Widget, direction: Direction) -> None:
        # Find matching schema entry
        for navigation_source, direction_map in self._schema.items():
            if isinstance(navigation_source, DomQuery):
                navigation_sources = list(self.app.query(navigation_source))
            else:
                navigation_sources = [navigation_source]
            for navigation_source in navigation_sources:
                if navigation_source == from_widget:
                    navigation_target = direction_map.get(direction)
                    if isinstance(navigation_target, DomQuery):
                        navigation_target = self.app.query_one(navigation_target)
                        navigation_target.focus()
                        print(navigation_source, direction, navigation_target)
                        return
                    elif isinstance(navigation_target, Widget):
                        navigation_target.focus()
                        print(navigation_source, direction, navigation_target)
                        return
                    elif callable(navigation_target):
                        navigation_target(from_widget, direction)
                        print(navigation_source, direction, navigation_target)
                        return
