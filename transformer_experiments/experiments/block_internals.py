# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/experiments/block-internals.ipynb.

# %% auto 0
__all__ = ['BlockInternalsAccessors', 'BlockInternalsExperiment', 'GetFilenameForBatchAndBlock',
           'BatchedBlockInternalsExperiment', 'run', 'BatchedBlockInternalsExperimentSlicer', 'BlockInternalsAnalysis']

# %% ../../nbs/experiments/block-internals.ipynb 5
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
import json
import math
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)

# %% ../../nbs/experiments/block-internals.ipynb 6
import click
import torch
from tqdm.auto import tqdm

# %% ../../nbs/experiments/block-internals.ipynb 7
from ..common.databatcher import DataBatcher
from ..common.substring_generator import all_unique_substrings
from ..common.utils import topk_across_batches
from ..dataset_split import split_text_dataset
from transformer_experiments.datasets.tinyshakespeare import (
    TinyShakespeareDataSet,
)
from transformer_experiments.models.transformer import (
    block_size,
    n_embed,
    n_layer,
    TransformerLanguageModel,
)
from transformer_experiments.models.transformer_helpers import (
    EncodingHelpers,
    LogitsWrapper,
    TransformerAccessors,
)
from ..tokenizers.char_tokenizer import CharacterTokenizer
from transformer_experiments.trained_models.tinyshakespeare_transformer import (
    create_model_and_tokenizer,
)

# %% ../../nbs/experiments/block-internals.ipynb 8
class BlockInternalsAccessors:
    """Helper class that provides easy access to the block internals values
    for a given prompt."""

    def __init__(
        self, prompt: str, eh: EncodingHelpers, accessors: TransformerAccessors
    ):
        self.prompt = prompt
        self.eh = eh
        self.accessors = accessors

        tokens = self.eh.tokenize_string(prompt)
        self.embedding = accessors.embed_tokens(tokens)

        _, self.io_accessors = accessors.run_model(self.embedding)

    def input_embedding(self) -> torch.Tensor:
        """Returns the input to the specified block."""
        return self.embedding

    def block_input(self, block_idx: int) -> torch.Tensor:
        """Returns the input to the specified block."""
        return self.io_accessors[block_idx].input(".")

    def heads_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the attention heads in the specified block."""
        # Heads output is the input to the self-attention proj layer.
        return self.io_accessors[block_idx].input("sa.proj")

    def proj_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the self-attention proj layer in the specified block."""
        return self.io_accessors[block_idx].output("sa.proj")

    def ffwd_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the feed-forward layer in the specified block."""
        return self.io_accessors[block_idx].output("ffwd")

    def block_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the specified block."""
        return self.io_accessors[block_idx].output(".")

# %% ../../nbs/experiments/block-internals.ipynb 12
class BlockInternalsExperiment:
    """An experiment to run a bunch of inputs through the model and save the
    intermediate values produced within each block."""

    def __init__(
        self,
        eh: EncodingHelpers,
        accessors: TransformerAccessors,
        strings: Sequence[str],
    ):
        self.eh = eh
        self.accessors = accessors
        self.strings = strings

        tokens = self.eh.tokenize_strings(self.strings)
        self.embeddings = self.accessors.embed_tokens(tokens)

        # Create a map of string to index to enable fast lookup.
        self.idx_map = OrderedDict((s, idx) for idx, s in enumerate(self.strings))

        # Run the embeddings through the model.
        _, self.io_accessors = self.accessors.run_model(self.embeddings)

    def string_idx(self, s: str) -> int:
        """Returns the index of the specified string."""
        return self.idx_map[s]

    def block_input(self, block_idx: int) -> torch.Tensor:
        """Returns the input to the specified block."""
        return self.io_accessors[block_idx].input(".")

    def heads_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the attention heads in the specified block."""
        # Heads output is the input to the self-attention proj layer.
        return self.io_accessors[block_idx].input("sa.proj")

    def proj_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the self-attention proj layer in the specified block."""
        return self.io_accessors[block_idx].output("sa.proj")

    def ffwd_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the feed-forward layer in the specified block."""
        return self.io_accessors[block_idx].output("ffwd")

    def block_output(self, block_idx: int) -> torch.Tensor:
        """Returns the output of the specified block."""
        return self.io_accessors[block_idx].output(".")

# %% ../../nbs/experiments/block-internals.ipynb 14
def batch_distances(batch: torch.Tensor, queries: torch.Tensor) -> torch.Tensor:
    """Returns the distance between each item in the batch and the queries."""
    assert batch.dim() == 2, f"batch.dim() should be 2, was {batch.dim()}"
    assert queries.dim() == 2, f"query.dim() should be 2, was {queries.dim()}"
    assert (
        batch.shape[-1] == queries.shape[-1]
    ), f"last dimension of batch was {batch.shape[-1]}, which does not match last dimension of queries {queries.shape[-1]}"

    B, _ = batch.shape
    n_queries, _ = queries.shape

    distances = torch.norm(
        # Reshape the batch to a singleton dimension, then expand that dimension
        # by the number of queries. We can then subtract all the queries in one
        # go.
        batch.reshape(B, 1, -1).expand(-1, n_queries, -1) - queries,
        dim=2,
    )
    return distances

# %% ../../nbs/experiments/block-internals.ipynb 15
class GetFilenameForBatchAndBlock(Protocol):
    """A protocol for a function that returns a filename for given batch
    and block indices."""

    def __call__(self, batch_idx: int, block_idx: int) -> Path:
        ...

# %% ../../nbs/experiments/block-internals.ipynb 16
class BatchedBlockInternalsExperiment:
    """Similar to BlockInternalsExperiment but rather than running
    all strings as one batch through the model, this one runs them
    in batches and writes results to disk. This makes it possible to
    run the analysis on longer strings."""

    def __init__(
        self,
        eh: EncodingHelpers,
        accessors: TransformerAccessors,
        strings: Sequence[str],
        output_dir: Path,
        batch_size: int = 10000,
    ):
        self.eh = eh
        self.accessors = accessors
        self.strings = strings
        self.output_dir = output_dir
        self.batch_size = batch_size

        # Create a map of string to index to enable fast lookup.
        self.idx_map = OrderedDict((s, idx) for idx, s in enumerate(self.strings))

        self.n_batches = math.ceil(len(self.strings) / self.batch_size)

    def sample_length(self) -> int:
        return len(self.strings[0])

    def run(self, disable_progress_bars: bool = False):
        for batch_idx in tqdm(range(self.n_batches), disable=disable_progress_bars):
            start_idx = batch_idx * self.batch_size
            end_idx = start_idx + self.batch_size
            batch_strings = self.strings[start_idx:end_idx]
            self._run_batch(batch_idx, batch_strings)

    def _embeddings_filename(self, batch_idx: int) -> Path:
        return self.output_dir / f"embeddings-{batch_idx:03d}.pt"

    def _block_input_filename(self, batch_idx: int, block_idx: int) -> Path:
        return self.output_dir / f"block_input-{batch_idx:03d}-{block_idx:02d}.pt"

    def _heads_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return self.output_dir / f"heads_output-{batch_idx:03d}-{block_idx:02d}.pt"

    def _proj_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return self.output_dir / f"proj_output-{batch_idx:03d}-{block_idx:02d}.pt"

    def _ffwd_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return self.output_dir / f"ffwd_output-{batch_idx:03d}-{block_idx:02d}.pt"

    def _block_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return self.output_dir / f"block_output-{batch_idx:03d}-{block_idx:02d}.pt"

    def _run_batch(self, batch_idx: int, batch_strings: Sequence[str]):
        tokens = self.eh.tokenize_strings(batch_strings)
        embeddings = self.accessors.embed_tokens(tokens)

        torch.save(embeddings, self._embeddings_filename(batch_idx))

        # Run the embeddings through the model.
        _, io_accessors = self.accessors.run_model(embeddings)

        # Write the results to disk.
        for block_idx, io_accessor in enumerate(io_accessors):
            torch.save(
                io_accessor.input("."),
                self._block_input_filename(batch_idx, block_idx),
            )
            torch.save(
                io_accessor.input("sa.proj"),
                self._heads_output_filename(batch_idx, block_idx),
            )
            torch.save(
                io_accessor.output("sa.proj"),
                self._proj_output_filename(batch_idx, block_idx),
            )
            torch.save(
                io_accessor.output("ffwd"),
                self._ffwd_output_filename(batch_idx, block_idx),
            )
            torch.save(
                io_accessor.output("."),
                self._block_output_filename(batch_idx, block_idx),
            )

    def string_idx(self, s: str) -> int:
        """Returns the index of the specified string."""
        return self.idx_map[s]

    def strings_from_indices(
        self, indices: torch.Tensor, alt_all_strings: Sequence[str] = []
    ) -> List[List[str]]:
        """Returns the strings corresponding to the specified indices.
        Indices is expected to be of shape (k, n). The returned list
        will have n elements, each of which is a list of k strings."""
        _, n = indices.shape

        all_strings = self.strings

        if len(alt_all_strings) > 0:
            all_strings = alt_all_strings

        # We're going to return a list of lists of strings. The
        # string at index [i][j] in the returned list is the
        # string corresponding to indices[j, i].
        strings: List[List[str]] = [[] for _ in range(n)]

        for ind in indices:
            for i, idx in enumerate(ind):
                strings[i].append(all_strings[idx])

        return strings

    def strings_with_topk_closest_embeddings(
        self,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest embeddings
        to the specified query."""

        n_queries, _, _ = queries.shape

        def _process_batch(batch: torch.Tensor) -> torch.Tensor:
            B, _, _ = batch.shape
            # Batch and queries and both shape (B, s_len, n_embed).
            # For the purposes of finding the closest values, we
            # reshape both the batch and queries to eliminate the
            # s_len dimension, effectively concatenating all the
            # embedding tensors across positions.
            return batch_distances(batch.reshape(B, -1), queries.reshape(n_queries, -1))

        values, indices = topk_across_batches(
            n_batches=self.n_batches,
            k=k,
            largest=largest,
            load_batch=lambda i: torch.load(
                str(self._embeddings_filename(i)), mmap=True
            ),
            process_batch=_process_batch,
        )

        return self.strings_from_indices(indices), values

    def _convert_t_i(self, t_i: int) -> int:
        """Converts a negative t_i to a positive one."""
        if t_i < 0:
            t_i = self.sample_length() + t_i

        assert t_i >= 0, f"converted t_i must be >= 0, was {t_i}"
        return t_i

    def _unique_substring_map(self, t_i: int) -> OrderedDict[str, int]:
        """Returns a map of unique substrings to indices."""
        t_i = self._convert_t_i(t_i)
        assert (
            t_i < self.sample_length() - 1
        ), f"t_i must be less than {self.sample_length() - 1} to generate unique substring map, was {t_i}"

        od = OrderedDict()
        # Insert substrings in order of first appearance.
        for i, s in enumerate(self.strings):
            substring = s[: t_i + 1]
            if substring not in od:
                od[substring] = i
        return od

    def _strings_with_topk_closest_outputs(
        self,
        get_filename: GetFilenameForBatchAndBlock,
        block_idx: int,
        t_i: int,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest outputs
        to the specified query, using the given `get_filename`
        function to load batches of the output data."""

        t_i = self._convert_t_i(t_i)

        all_strings = self.strings
        unique_substring_indices: Optional[torch.Tensor] = None

        # If the requested t_i is not the last character, we
        # need to compute the unique substrings of length t_i + 1.
        # We'll only evaluate outputs for these unique substrings.
        if t_i < self.sample_length() - 1:
            unique_substring_map = self._unique_substring_map(t_i)
            all_strings = list(unique_substring_map.keys())

            # The keys of the ordered dictionary are the indices into
            # self.strings i.e. the global indices of the unique substrings.
            unique_substring_indices = torch.tensor(list(unique_substring_map.values()))

        def _load_batch(batch_idx: int) -> torch.Tensor:
            if t_i == self.sample_length() - 1:
                # If we're looking at the last character, we can just
                # load the batch and index it directly.
                return torch.load(
                    str(get_filename(batch_idx=batch_idx, block_idx=block_idx)),
                    mmap=True,
                )[:, t_i, :]

            # Otherwise, we need to find just the unique substrings that
            # appear in the batch and return the subset of the batch
            # containing them.
            assert unique_substring_indices is not None

            # Find the indices of the unique substrings that appear
            # in the batch we're asked to load.
            mask = (unique_substring_indices >= batch_idx * self.batch_size) & (
                unique_substring_indices < (batch_idx + 1) * self.batch_size
            )
            batch_indices = (
                unique_substring_indices[torch.nonzero(mask).squeeze(dim=1)]
                - batch_idx * self.batch_size
            )
            assert (
                batch_indices.shape[0] > 0
            ), f"batch_indices were empty for batch_idx {batch_idx}"

            return torch.load(
                str(get_filename(batch_idx=batch_idx, block_idx=block_idx)),
                mmap=True,
            )[batch_indices, t_i, :]

        def _process_batch(batch: torch.Tensor) -> torch.Tensor:
            return batch_distances(batch, queries=queries)

        values, indices = topk_across_batches(
            n_batches=self.n_batches,
            k=k,
            largest=largest,
            load_batch=_load_batch,
            process_batch=_process_batch,
        )
        return self.strings_from_indices(indices, alt_all_strings=all_strings), values

    def strings_with_topk_closest_proj_outputs(
        self,
        block_idx: int,
        t_i: int,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest proj outputs
        to the specified query."""
        return self._strings_with_topk_closest_outputs(
            get_filename=self._proj_output_filename,
            block_idx=block_idx,
            t_i=t_i,
            queries=queries,
            k=k,
            largest=largest,
        )

    def strings_with_topk_closest_ffwd_outputs(
        self,
        block_idx: int,
        t_i: int,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest ffwd outputs
        to the specified query."""

        return self._strings_with_topk_closest_outputs(
            get_filename=self._ffwd_output_filename,
            block_idx=block_idx,
            t_i=t_i,
            queries=queries,
            k=k,
            largest=largest,
        )

# %% ../../nbs/experiments/block-internals.ipynb 18
@click.command()
@click.argument("model_weights_filename", type=click.Path(exists=True))
@click.argument("dataset_cache_filename", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=True))
@click.option(
    "-s",
    "--sample_len",
    required=True,
    type=click.IntRange(min=1, max=block_size),
)
@click.option(
    "-m",
    "--max_batch_size",
    required=False,
    type=click.IntRange(min=1),
    default=10000,
)
def run(
    model_weights_filename: str,
    dataset_cache_filename: str,
    output_folder: str,
    sample_len: int,
    max_batch_size: int,
):
    click.echo(f"Running block internals experiment for with:")
    click.echo(f"  model weights: {model_weights_filename}")
    click.echo(f"  dataset cache: {dataset_cache_filename}")
    click.echo(f"  output folder: {output_folder}")
    click.echo(f"  sample length: {sample_len}")
    click.echo(f"  max batch size: {max_batch_size}")

    # Instantiate the model, tokenizer, and dataset
    device = "cuda" if torch.cuda.is_available() else "cpu"
    click.echo(f"device is {device}")

    ts = TinyShakespeareDataSet(cache_file=dataset_cache_filename)
    m, tokenizer = create_model_and_tokenizer(
        saved_model_filename=model_weights_filename,
        dataset=ts,
        device=device,
    )

    strings = all_unique_substrings(ts.text, sample_len)

    encoding_helpers = EncodingHelpers(tokenizer, device)
    accessors = TransformerAccessors(m, device)

    # Create the experiment
    exp = BatchedBlockInternalsExperiment(
        encoding_helpers, accessors, strings, Path(output_folder), max_batch_size
    )

    exp.run()

# %% ../../nbs/experiments/block-internals.ipynb 19
class BatchedBlockInternalsExperimentSlicer:
    """Companion class to BatchedBlockInternalsExperiment that "slices" the
    data files along a particular t_i dimension to make for faster loading
    when computing closest proj outputs and ffwd outputs."""

    def __init__(
        self,
        exp: BatchedBlockInternalsExperiment,
        output_dir: Path,
        t_i: int,
        combine_n_batches: int = 10,
    ):
        self.exp = exp
        self.output_dir = output_dir

        # Convert negative indices to positive
        if t_i < 0:
            t_i = self.exp.sample_length() + t_i

        assert t_i >= 0, f"converted t_i must be >= 0, was {t_i}"

        self.t_i = t_i
        self.combine_n_batches = combine_n_batches

        self.batch_size = exp.batch_size * combine_n_batches
        self.n_batches = math.ceil(len(exp.strings) / self.batch_size)

    def _proj_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return (
            self.output_dir
            / f"proj_output-{batch_idx:03d}-{block_idx:02d}-{self.t_i:03d}.pt"
        )

    def _ffwd_output_filename(self, batch_idx: int, block_idx: int) -> Path:
        return (
            self.output_dir
            / f"ffwd_output-{batch_idx:03d}-{block_idx:02d}-{self.t_i:03d}.pt"
        )

    def create_slices(
        self,
        get_in_filename: Callable[[int, int], Path],
        get_out_filename: Callable[[int, int], Path],
        disable_progress_bars: bool = False,
    ):
        for block_idx in range(n_layer):
            slices = []
            for batch_idx in tqdm(
                range(self.exp.n_batches), disable=disable_progress_bars
            ):
                batch = torch.load(get_in_filename(batch_idx, block_idx))
                slices.append(batch[:, self.t_i, :].clone())

                if (batch_idx + 1) % self.combine_n_batches == 0:
                    torch.save(
                        torch.cat(slices),
                        get_out_filename(
                            batch_idx // self.combine_n_batches, block_idx
                        ),
                    )
                    slices = []
            if len(slices) > 0:
                torch.save(
                    torch.cat(slices),
                    get_out_filename(batch_idx // self.combine_n_batches, block_idx),
                )
                slices = []

    def create_proj_output_slices(self, disable_progress_bars: bool = False):
        self.create_slices(
            self.exp._proj_output_filename,
            self._proj_output_filename,
            disable_progress_bars=disable_progress_bars,
        )

    def create_ffwd_output_slices(self, disable_progress_bars: bool = False):
        self.create_slices(
            self.exp._ffwd_output_filename,
            self._ffwd_output_filename,
            disable_progress_bars=disable_progress_bars,
        )

    def create_slices_if_needed(self, disable_progress_bars: bool = False):
        if not self.output_dir.exists():
            raise ValueError(f"{self.output_dir} does not exist")

        try:
            _ = next(iter(self.output_dir.glob(f"proj_output*-{self.t_i:03d}.pt")))
        except StopIteration:
            self.create_proj_output_slices(disable_progress_bars=disable_progress_bars)

        try:
            _ = next(iter(self.output_dir.glob(f"ffwd_output*-{self.t_i:03d}.pt")))
        except StopIteration:
            self.create_ffwd_output_slices(disable_progress_bars=disable_progress_bars)

    def strings_with_topk_closest_proj_outputs(
        self,
        block_idx: int,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest proj outputs
        to the specified query."""
        n_queries, _ = queries.shape
        values, indices = topk_across_batches(
            n_batches=self.n_batches,
            k=k,
            largest=largest,
            load_batch=lambda i: torch.load(
                str(self._proj_output_filename(i, block_idx)), mmap=True
            ),
            process_batch=lambda batch: batch_distances(batch, queries=queries),
        )
        return self.exp.strings_from_indices(indices), values

    def strings_with_topk_closest_ffwd_outputs(
        self,
        block_idx: int,
        queries: torch.Tensor,
        k: int,
        largest: bool = True,
    ) -> Tuple[Sequence[Sequence[str]], torch.Tensor]:
        """Returns the top k strings with the closest ffwd outputs
        to the specified query."""
        n_queries, _ = queries.shape
        values, indices = topk_across_batches(
            n_batches=self.n_batches,
            k=k,
            largest=largest,
            load_batch=lambda i: torch.load(
                str(self._ffwd_output_filename(i, block_idx)), mmap=True
            ),
            process_batch=lambda batch: batch_distances(batch, queries=queries),
        )
        return self.exp.strings_from_indices(indices), values

# %% ../../nbs/experiments/block-internals.ipynb 21
class BlockInternalsAnalysis:
    """This class performs analysis of how the next token probabilities change
    as an embedded input is passed through each of the blocks in the model"""

    def __init__(
        self,
        accessors: TransformerAccessors,
        encoding_helpers: EncodingHelpers,
        prompt: str,
    ):
        self.accessors = accessors
        self.encoding_helpers = encoding_helpers
        self.prompt = prompt

        # Run the prompt through the model
        tokens = self.encoding_helpers.tokenize_string(prompt)
        x = self.accessors.embed_tokens(tokens)
        _, io_accessors = self.accessors.run_model(x)

        tokenizer = self.encoding_helpers.tokenizer

        # The data tensor is going to be a stack of probabilities. Columns
        # correspond to tokens.
        #
        # Row index 0 is the probabilities from the input embedding.
        # Row index 1 + 2 * block_idx is the probabilities that result from
        #   adding block block_idx's self-attention output to its input.
        # Row index 1 + 2 * block_idx + 1 is the probabilities that result from
        #   adding block block_idx's feed-forward output to the previous result.
        #
        # Examples:
        #   self.data[0][tokenizer.stoi['a']] is the probability of the next
        #       token being 'a' given the input embedding.
        #   self.data[1][tokenizer.stoi['a']] is the probability of the next
        #       token being 'a' given the input embedding plus the self-attention
        #       output of the first block.
        #   self.data[2][tokenizer.stoi['a']] is the probability of the next
        #       token being 'a' given the input embedding plus the self-attention
        #       output of the first block plus the feed-forward output of the
        #       first block.
        #   self.data[3][tokenizer.stoi['a']] is the probability of the next
        #       token being 'a' given the output of the first block plus the
        #       self-attention output of the second block.
        self.data = torch.zeros(
            (1 + 2 * n_layer, tokenizer.vocab_size), dtype=torch.float32
        )
        self.data[0] = LogitsWrapper(
            self.accessors.logits_from_embedding(x), tokenizer
        ).probs()[0, -1]
        self.row_labels = ["Input"]
        for block_idx, io_accessor in enumerate(io_accessors):
            block_input = io_accessor.input(".")
            sa_output = io_accessor.output("sa")
            ffwd_output = io_accessor.output("ffwd")

            # The logic inside a block is:
            #   x = x + self.sa(self.ln1(x))
            #   x = x + self.ffwd(self.ln2(x))
            #
            # sa_adjusted_logits simulates the first line
            # and ffwd_adjusted_logits simulates the second line.

            sa_adjusted_logits = LogitsWrapper(
                self.accessors.logits_from_embedding(block_input + sa_output), tokenizer
            )
            self.data[self.idx_sa_probs(block_idx)] = sa_adjusted_logits.probs()[0, -1]
            self.row_labels.append(f"Block {block_idx} after SA")

            ffwd_adjusted_logits = LogitsWrapper(
                self.accessors.logits_from_embedding(
                    block_input + sa_output + ffwd_output
                ),
                tokenizer,
            )
            self.data[self.idx_ffwd_probs(block_idx)] = ffwd_adjusted_logits.probs()[
                0, -1
            ]
            self.row_labels.append(f"Block {block_idx} after FFWD")

    def idx_sa_probs(self, block_idx: int) -> int:
        """Returns the index into the data tensor containing the SA adjusted
        probabilities for the given block index."""
        return 1 + 2 * block_idx

    def idx_ffwd_probs(self, block_idx: int) -> int:
        """Returns the index into the data tensor containing the ffwd adjusted
        probabilities for the given block index."""
        return 1 + 2 * block_idx + 1

    def idx_input_probs(self, block_idx) -> int:
        """Returns the index into the data tensor containing the probabilities
        from the input to the given block index."""
        return self.idx_sa_probs(block_idx) - 1

    def plot(self):
        _, ax = plt.subplots(1, 1, figsize=(20, 12))
        self._plot(
            ax,
            self.data,
            self.row_labels,
            [repr(c)[1:-1] for c in self.encoding_helpers.tokenizer.chars],
        )

    def plot_subset(self, rows: Sequence[int] = [], cols: Sequence[int] = []):
        # If either rows or cols is empty, treat is as "all"
        if len(rows) == 0:
            rows = range(self.data.shape[0])
        if len(cols) == 0:
            cols = range(self.data.shape[1])

        data = torch.zeros((len(rows), len(cols)), dtype=self.data.dtype)
        for i, row in enumerate(rows):
            for j, col in enumerate(cols):
                data[i, j] = self.data[row, col]

        row_labels = [self.row_labels[row] for row in rows]
        col_labels = [
            repr(self.encoding_helpers.tokenizer.itos[col])[1:-1] for col in cols
        ]

        _, ax = plt.subplots(1, 1, figsize=(len(cols), len(rows)))
        self._plot(ax, data, row_labels, col_labels)

    def _plot(
        self,
        ax: Axes,
        data: torch.Tensor,
        row_labels: Sequence[str],
        col_labels: Sequence[str],
    ):
        im = ax.imshow(data, cmap="viridis")
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=90)

        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
        im.set_clim(0, 1.0)

        plt.colorbar(im, ax=[ax], location="top")
