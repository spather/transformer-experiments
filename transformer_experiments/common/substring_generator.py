# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/common/substring-generator.ipynb.

# %% auto 0
__all__ = ['SubstringGenerator', 'all_unique_substrings']

# %% ../../nbs/common/substring-generator.ipynb 5
from collections import OrderedDict
from typing import Sequence

# %% ../../nbs/common/substring-generator.ipynb 6
class SubstringGenerator:
    """Iterable that produces all possible substrings of a given
    length from a given text."""

    def __init__(self, text: str, substring_length: int):
        if len(text) < substring_length:
            raise ValueError(
                "Text length must be greater than or equal to substring length."
            )

        if substring_length < 1:
            raise ValueError("Substring length must be greater than or equal to 1.")

        self.text = text
        self.substring_length = substring_length

    def __len__(self):
        return len(self.text) - self.substring_length + 1

    def __iter__(self):
        for i in range(len(self.text) - self.substring_length + 1):
            yield self.text[i : i + self.substring_length]

# %% ../../nbs/common/substring-generator.ipynb 8
def all_unique_substrings(text: str, substring_length: int) -> Sequence[str]:
    """Returns all unique substrings of a given length from a given text.
    Substrings are returned in the order of first occurrence in the text."""
    sg = SubstringGenerator(text, substring_length)
    od: OrderedDict[str, None] = OrderedDict()
    for substring in sg:
        # only insert if not already present, which ensures the
        # order of first occurrence is preserved
        if substring not in od:
            od[substring] = None
    return list(od.keys())
