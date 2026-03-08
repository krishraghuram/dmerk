from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, TypeVar

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input

from dmerk.tui.mixins.refresh import DmerkRefreshable
from dmerk.utils import fuzzy_match

if TYPE_CHECKING:
    from textual.widget import Widget as _WidgetBase
else:
    _WidgetBase = object

T = TypeVar("T")


class FilterMixin(_WidgetBase):
    """
    Mixin providing filtering functionality for Textual widgets.

    Must be used with a textual.widget.Widget subclass.

    Provides the following:
    - filter_by: reactive[str] - current filter text
    - on_input_changed: handles Input.Changed events
    - filter(): filters iterables by fuzzy-matching
    - Auto-refresh: If widget implements DmerkRefreshable, it will be automatically refreshed when filter_by changes.
    - Otherwise, widget needs to implement watch_filter_by to be notified of filter_by changes.

    Example:
        class MyWidget(FilterMixin, Static):
            # Auto-called when filter changes
            async def _refresh(self) -> None:
                await self._refresh_table()
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
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

    async def watch_filter_by(self) -> None:
        if isinstance(self, DmerkRefreshable):
            await self._refresh()
