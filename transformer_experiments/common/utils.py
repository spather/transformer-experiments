# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/common/utils.ipynb.

# %% auto 0
__all__ = ['T', 'aggregate_by_string_key', 'DataWrapper']

# %% ../../nbs/common/utils.ipynb 4
from typing import Callable, Dict, Generic, Iterable, TypeVar

# %% ../../nbs/common/utils.ipynb 5
T = TypeVar("T")  # Generic type that will be used in many places

# %% ../../nbs/common/utils.ipynb 6
def aggregate_by_string_key(
    items: Iterable[T], key: Callable[[T], str]
) -> Dict[str, T]:
    """Aggregates an iterable of items into a dictionary, where the key is the result of
    applying the key function to the item. If multiple items have the same key, the
    last item is used."""
    return {key(item): item for item in items}

# %% ../../nbs/common/utils.ipynb 8
class DataWrapper(Generic[T]):
    def __init__(
        self,
        data: Iterable[T],
        format_item_fn: Callable[[T], str] = repr,
    ):
        self.data = data
        self.format_item_fn = format_item_fn

    def __repr__(self):
        return f"DataWrapper({repr(self.data)})"

    def __str__(self):
        return ", ".join([self.format_item_fn(d) for d in self.data])

    def print(self):
        for d in self.data:
            print(self.format_item_fn(d))
