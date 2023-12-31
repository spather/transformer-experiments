# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/common/utils.ipynb.

# %% auto 0
__all__ = ['T', 'aggregate_by_string_key', 'DataWrapper', 'topk_across_batches']

# %% ../../nbs/common/utils.ipynb 4
from typing import Callable, Dict, Generic, Iterable, Sequence, Tuple, TypeVar

# %% ../../nbs/common/utils.ipynb 5
import torch

# %% ../../nbs/common/utils.ipynb 6
T = TypeVar("T")  # Generic type that will be used in many places

# %% ../../nbs/common/utils.ipynb 7
def aggregate_by_string_key(
    items: Iterable[T], key: Callable[[T], str]
) -> Dict[str, T]:
    """Aggregates an iterable of items into a dictionary, where the key is the result of
    applying the key function to the item. If multiple items have the same key, the
    last item is used."""
    return {key(item): item for item in items}

# %% ../../nbs/common/utils.ipynb 9
class DataWrapper(Generic[T]):
    def __init__(
        self,
        data: Sequence[T],
        format_item_fn: Callable[[T], str] = repr,
    ):
        self.data = data
        self.format_item_fn = format_item_fn

    def __repr__(self):
        return f"DataWrapper({repr(self.data)})"

    def __str__(self):
        return ", ".join([self.format_item_fn(d) for d in self.data])

    def __getitem__(self, i):
        return self.data[i]

    def print(self):
        for d in self.data:
            print(self.format_item_fn(d))

# %% ../../nbs/common/utils.ipynb 11
def topk_across_batches(
    n_batches: int,
    k: int,
    largest: bool,
    load_batch: Callable[[int], torch.Tensor],
    process_batch: Callable[[torch.Tensor], torch.Tensor],
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Like torch.topk, but works across multiple batches of data. Always
    works over the batch dimension, which is assumed to be the first dimension
    of each batch.

    Parameters:
    -----------
    n_batches:
        The number of batches to process.
    k:
        The number of top values to return.
    largest:
        Whether to return the largest or smallest values.
    load_batch:
        A function that takes a batch index and returns a batch of data.
    process_batch:
        A function that takes a batch of data and returns a tensor of
        values, with the same first dimension size as the batch. The function
        will return the top k of these values along the batch dimension.

    Returns:
    --------
        A tuple of (values, indices) where indices is a list of indices into
        the overall dataset i.e. across all batches.
    """
    all_topk_values = []
    all_topk_indices = []

    batch_sizes = []
    # Go through each batch and find the top k closest items
    # within that batch.
    for batch_idx in range(n_batches):
        batch = load_batch(batch_idx)

        results = process_batch(batch)

        assert (
            results.shape[0] == batch.shape[0]
        ), f"Batch had {batch.shape[0]} items, but results had {results.shape[0]} items."
        assert batch.shape[0] >= k, f"Batch had {batch.shape[0]} items, but k was {k}."

        batch_sizes.append(batch.shape[0])

        topk_values, topk_indices = torch.topk(results, k=k, largest=largest, dim=0)
        all_topk_values.append(topk_values)
        all_topk_indices.append(topk_indices)

    # Combine the results from all batches.
    all_topk_values_tensor = torch.cat(all_topk_values)
    all_topk_indices_tensor = torch.cat(all_topk_indices)

    # Find the topk items across all batches.
    topk = torch.topk(all_topk_values_tensor, k=k, largest=largest, dim=0)
    topk_overall_values: torch.Tensor = topk.values

    # Now we have to do math to translate the indices into all_topk_distances
    # into indices across all data items across all batches.

    # First, calculate the cumulative sum of the batch sizes.
    # Stick a zero at the front so that we can index into this
    # with batch_idx and know how many items were in all the
    # previous batches.
    prev_batch_sums = torch.cat(
        [
            torch.tensor([0], device=all_topk_values_tensor.device),
            torch.cumsum(
                torch.tensor(batch_sizes, device=all_topk_values_tensor.device), dim=0
            ),
        ]
    )

    topk_overall_indices = []
    for i in topk.indices:
        # i is the index into all_topk_distances. First, let's figure
        # out which batch it came from.
        batch_idx = i // k

        # Now we need to figure out which index into that batch it was.
        # all_topk_indices has the indices from the topk operation on
        # each batch.
        index_within_batch = torch.gather(
            all_topk_indices_tensor, dim=0, index=i.unsqueeze(0)
        ).squeeze(0)

        # The overall index is the sum of the number of items in all
        # previous batches, plus the index within the current batch.
        topk_overall_indices.append(prev_batch_sums[batch_idx] + index_within_batch)

    return topk_overall_values, torch.stack(topk_overall_indices)
