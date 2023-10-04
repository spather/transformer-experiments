# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/experiments/block-internals.ipynb.

# %% auto 0
__all__ = ['BlockInternalsResult', 'BlockInternalsExperiment', 'run']

# %% ../../nbs/experiments/block-internals.ipynb 5
import argparse
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Iterator, Tuple

# %% ../../nbs/experiments/block-internals.ipynb 6
import click
import torch
from tqdm.auto import tqdm

# %% ../../nbs/experiments/block-internals.ipynb 7
from ..common import DataBatcher
from ..dataset_split import split_text_dataset
from transformer_experiments.datasets.tinyshakespeare import (
    TinyShakespeareDataSet,
)
from transformer_experiments.models.transformer import (
    n_embed,
    n_layer,
    TransformerLanguageModel,
)
from transformer_experiments.models.transformer_helpers import (
    EncodingHelpers,
    TransformerAccessors,
)
from transformer_experiments.trained_models.tinyshakespeare_transformer import (
    create_model_and_tokenizer,
)

# %% ../../nbs/experiments/block-internals.ipynb 8
@dataclass
class BlockInternalsResult:
    substring: str
    heads_output: torch.Tensor
    proj_output: torch.Tensor
    ffwd_output: torch.Tensor

# %% ../../nbs/experiments/block-internals.ipynb 9
class BlockInternalsExperiment:
    """An experiment to run a bunch of inputs through a block and save the
    intermediate values produced for each token."""

    def __init__(
        self,
        eh: EncodingHelpers,
        accessors: TransformerAccessors,
        block_idx: int,
        results_folder: Path,
    ):
        assert block_idx >= 0 and block_idx < n_layer

        self.eh = eh
        self.accessors = accessors
        self.block_idx = block_idx
        self.results_folder = results_folder

    def _filename_stem(self):
        return f"block{self.block_idx}_internals"

    def _input_filename(self, batch: int):
        return f"{self._filename_stem()}_input_{batch:03d}.pt"

    def _head_output_filename(self, batch: int):
        return f"{self._filename_stem()}_head_output_{batch:03d}.pt"

    def _proj_output_filename(self, batch: int):
        return f"{self._filename_stem()}_proj_output_{batch:03d}.pt"

    def _ffwd_output_filename(self, batch: int):
        return f"{self._filename_stem()}_ffwd_output_{batch:03d}.pt"

    def run(self, data_batcher: DataBatcher):
        for batch_idx, batch in tqdm(enumerate(data_batcher)):
            x = self.eh.embed_tokens(batch)

            # Run the encoded batch through the blocks up to the one we're interested in
            for i in range(self.block_idx):
                x = self.accessors.m.blocks[i](x)

            # Copy the block we're interested in
            block, io_accessor = self.accessors.copy_block_from_model(
                block_idx=self.block_idx
            )
            _ = block(x)  # Run the block

            # Grab the outputs of interest
            heads_output = io_accessor.input("sa.proj")
            proj_output = io_accessor.output("sa.proj")
            ffwd_output = io_accessor.output("ffwd")

            torch.save(
                batch.clone(), self.results_folder / self._input_filename(batch_idx)
            )
            torch.save(
                heads_output,
                self.results_folder / self._head_output_filename(batch_idx),
            )
            torch.save(
                proj_output, self.results_folder / self._proj_output_filename(batch_idx)
            )
            torch.save(
                ffwd_output, self.results_folder / self._ffwd_output_filename(batch_idx)
            )

    def load(
        self,
    ) -> Iterator[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        input_files = sorted(
            self.results_folder.glob(f"{self._filename_stem()}_input_*.pt")
        )
        head_output_files = sorted(
            self.results_folder.glob(f"{self._filename_stem()}_head_output_*.pt")
        )
        proj_output_files = sorted(
            self.results_folder.glob(f"{self._filename_stem()}_proj_output_*.pt")
        )
        ffwd_output_files = sorted(
            self.results_folder.glob(f"{self._filename_stem()}_ffwd_output_*.pt")
        )

        assert (
            len(input_files)
            == len(head_output_files)
            == len(proj_output_files)
            == len(ffwd_output_files)
        )

        for input_file, head_output_file, proj_output_file, ffwd_output_file in zip(
            input_files, head_output_files, proj_output_files, ffwd_output_files
        ):
            assert input_file.exists()
            assert head_output_file.exists()
            assert proj_output_file.exists()
            assert ffwd_output_file.exists()

            yield torch.load(input_file), torch.load(head_output_file), torch.load(
                proj_output_file
            ), torch.load(ffwd_output_file)

    def raw_results(self) -> Iterator[BlockInternalsResult]:
        for inputs, head_output, proj_output, ffwd_output in self.load():
            n_samples, s_len = inputs.shape
            for i in range(n_samples):
                for j in range(s_len):
                    substring = self.eh.stringify_tokens(inputs[i][: j + 1])
                    yield BlockInternalsResult(
                        substring,
                        head_output[i][j],
                        proj_output[i][j],
                        ffwd_output[i][j],
                    )

# %% ../../nbs/experiments/block-internals.ipynb 13
@click.command()
@click.argument("model_weights_filename", type=click.Path(exists=True))
@click.argument("dataset_cache_filename", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=True))
@click.option(
    "-b",
    "--block_idx",
    required=True,
    type=click.IntRange(min=0, max=n_layer, max_open=True),
)
def run(
    model_weights_filename: str,
    dataset_cache_filename: str,
    output_folder: str,
    block_idx: int,
):
    click.echo(f"Running block internals experiment for block {block_idx}")

    # Instantiate the model, tokenizer, and dataset
    device = "cuda" if torch.cuda.is_available() else "cpu"
    click.echo(f"device is {device}")

    ts = TinyShakespeareDataSet(cache_file=dataset_cache_filename)
    m, tokenizer = create_model_and_tokenizer(
        saved_model_filename=model_weights_filename,
        dataset=ts,
        device=device,
    )
    _, val_data = split_text_dataset(ts.text, tokenizer, train_pct=0.9)

    encoding_helpers = EncodingHelpers(m, tokenizer, device)
    accessors = TransformerAccessors(m)

    # Create the experiment
    exp = BlockInternalsExperiment(
        encoding_helpers, accessors, block_idx, Path(output_folder)
    )

    # Run the experiment
    data_batcher = DataBatcher(
        data=val_data,
        sample_len=3,
        max_batch_size=64,
        stride=96,
    )
    exp.run(data_batcher=data_batcher)
