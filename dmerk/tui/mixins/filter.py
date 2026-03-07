from typing import TYPE_CHECKING, TypeVar, Callable, Iterable, Iterator

from textual.reactive import reactive
from textual.widgets import Input
from textual.widget import Widget

from dmerk.utils import fuzzy_match

if TYPE_CHECKING:
    from textual.widget import Widget as _WidgetBase
else:
    _WidgetBase = object

T = TypeVar("T")


class FilterMixin(_WidgetBase):
    """
    Mixin providing filtering functionality for Textual widgets.

    Must be used with a textual.widget.Widget subclass. Provides:
    - filter_by: reactive[str] - current filter text
    - on_input_changed: handles Input.Changed events
    - filter: filters iterables by fuzzy-matching

    Widgets must override watch_filter_by to refresh when filter changes.

    Example:
        class MyWidget(FilterMixin, Static):
            async def watch_filter_by(self) -> None:
                await self._refresh()
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Skip check for the mixin itself, check subclasses
        if not (cls is FilterMixin or issubclass(cls, Widget)):
            raise TypeError(f"{cls.__name__} must inherit from Widget")

    filter_by = reactive("")

    def on_input_changed(self, message: Input.Changed) -> None:
        self.filter_by = message.value

    def filter(self, items: Iterable[T], key: Callable[[T], str]) -> Iterator[T]:
        """
        Filter items where key(item) fuzzy-matches self.filter_by.

        Returns a single-use iterator. Materialize with list() if you need
        to iterate multiple times or sort the results.

        Args:
            items: Iterable of items to filter
            key: Function extracting searchable string from each item

        Returns:
            Iterator of filtered items
        """
        if not self.filter_by:
            return iter(items)
        return (item for item in items if fuzzy_match(key(item), self.filter_by))
