from typing import Protocol, runtime_checkable


@runtime_checkable
class DmerkRefreshable(Protocol):
    """
    Protocol for widgets that can be refreshed

    Prefixing with Dmerk to indicate that this specific to dmerk, and not related to textual.widget.Widget.refresh
    """

    async def _refresh(self) -> None: ...
