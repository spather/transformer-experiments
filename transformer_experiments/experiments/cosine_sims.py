# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/experiments/cosine-sims.ipynb.

# %% auto 0
__all__ = ['environment', 'CosineSimilaritiesExperiment', 'get_ffwd_queries', 'run']

# %% ../../nbs/experiments/cosine-sims.ipynb 5
import math
from pathlib import Path
import tempfile
from typing import Sequence

# %% ../../nbs/experiments/cosine-sims.ipynb 6
import click
import torch
import torch.nn as nn
from torch.nn import functional as F
from tqdm.auto import tqdm

# %% ../../nbs/experiments/cosine-sims.ipynb 7
from ..environments import get_environment
from ..common.substring_generator import all_unique_substrings
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
from transformer_experiments.trained_models.tinyshakespeare_transformer import (
    create_model_and_tokenizer,
)

# %% ../../nbs/experiments/cosine-sims.ipynb 8
class CosineSimilaritiesExperiment:
    def __init__(
        self,
        strings: Sequence[str],
        batch_size: int,
        output_folder: Path,
        encoding_helpers: EncodingHelpers,
        accessors: TransformerAccessors,
    ):
        self.strings = strings
        self.batch_size = batch_size
        self.output_folder = output_folder
        self.encoding_helpers = encoding_helpers
        self.accessors = accessors

        self.n_batches = math.ceil(len(self.strings) / self.batch_size)

    def cosine_sim_ffwd_out_filename(self, batch_idx: int) -> Path:
        return self.output_folder / f"cosine_sim_ffwd_out_{batch_idx:05d}.pt"

    def run(
        self,
        queries: torch.Tensor,
        start_batch_idx: int = 0,
        disable_progress_bar: bool = False,
    ):
        assert queries.dim() == 3
        assert queries.shape[0] == n_layer
        assert queries.shape[2] == n_embed
        n_queries = queries.shape[1]

        for batch_idx in tqdm(
            range(start_batch_idx, self.n_batches), disable=disable_progress_bar
        ):
            start_idx = batch_idx * self.batch_size
            end_idx = start_idx + self.batch_size
            batch_strings = self.strings[start_idx:end_idx]

            batch_size = len(
                batch_strings
            )  # Might be smaller than configured batch size
            assert batch_size <= self.batch_size

            ffwd_outs = self._get_ffwd_outs(
                batch_strings
            )  # (n_layer, batch_size, n_embed)

            sims = F.cosine_similarity(
                ffwd_outs.reshape(n_layer, batch_size, 1, n_embed).expand(
                    -1, -1, n_queries, -1
                ),
                queries.reshape(n_layer, 1, n_queries, n_embed).expand(
                    -1, batch_size, -1, -1
                ),
                dim=-1,
            )

            torch.save(sims, self.cosine_sim_ffwd_out_filename(batch_idx))

    def _get_ffwd_outs(self, batch_strings: Sequence[str]) -> torch.Tensor:
        tokens = self.encoding_helpers.tokenize_strings(batch_strings)
        embeddings = self.accessors.embed_tokens(tokens)

        _, io_accessors = self.accessors.run_model(embeddings)

        ffwd_outs = torch.stack(
            [
                io_accessors[block_idx].output("ffwd")[:, -1, :]
                for block_idx in range(n_layer)
            ]
        )
        return ffwd_outs

# %% ../../nbs/experiments/cosine-sims.ipynb 9
def get_ffwd_queries(
    strings: Sequence[str],
    encoding_helpers: EncodingHelpers,
    accessors: TransformerAccessors,
) -> torch.Tensor:
    tokens = encoding_helpers.tokenize_strings(strings)
    embeddings = accessors.embed_tokens(tokens)

    _, io_accessors = accessors.run_model(embeddings)

    return torch.stack(
        [
            io_accessors[block_idx].output("ffwd")[:, -1, :]
            for block_idx in range(n_layer)
        ]
    )

# %% ../../nbs/experiments/cosine-sims.ipynb 10
environment = get_environment()
print(f"environment is {environment.name}")

# %% ../../nbs/experiments/cosine-sims.ipynb 16
@click.command()
@click.argument("model_weights_filename", type=click.Path(exists=True))
@click.argument("dataset_cache_filename", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=True))
@click.option(
    "-s",
    "--string_len",
    required=True,
    type=click.IntRange(min=1, max=block_size),
)
@click.option(
    "-m",
    "--max_batch_size",
    required=True,
    type=click.IntRange(min=1),
)
@click.option(
    "-n",
    "--num_queries",
    required=True,
    type=click.IntRange(min=1),
)
@click.option(
    "-r",
    "--random_seed",
    required=True,
    type=click.INT,
)
@click.option(
    "-b",
    "--start_batch_idx",
    required=False,
    type=click.INT,
    default=0,
)
def run(
    model_weights_filename: str,
    dataset_cache_filename: str,
    output_folder: str,
    string_len: int,
    max_batch_size: int,
    num_queries: int,
    random_seed: int,
    start_batch_idx: int,
):
    click.echo("CosineSimilaritiesExperiment CLI")
    click.echo()
    click.echo(f"  model weights: {model_weights_filename}")
    click.echo(f"  dataset cache: {dataset_cache_filename}")
    click.echo(f"  output folder: {output_folder}")

    click.echo()
    click.echo(f"  string length: {string_len}")
    click.echo(f"  max batch size: {max_batch_size}")
    click.echo(f"  num queries: {num_queries}")
    click.echo(f"  random seed: {random_seed}")
    click.echo(f"  start batch idx: {start_batch_idx}")

    click.echo()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    click.echo(f"device is {device}")

    ts = TinyShakespeareDataSet(cache_file=dataset_cache_filename)
    m, tokenizer = create_model_and_tokenizer(
        saved_model_filename=model_weights_filename,
        dataset=ts,
        device=device,
    )
    _ = m.to(device)

    encoding_helpers = EncodingHelpers(tokenizer, device)
    accessors = TransformerAccessors(m, device)

    all_strings = all_unique_substrings(ts.text, string_len)

    experiment = CosineSimilaritiesExperiment(
        strings=all_strings,
        batch_size=max_batch_size,
        output_folder=Path(output_folder),
        encoding_helpers=encoding_helpers,
        accessors=accessors,
    )

    torch.manual_seed(random_seed)
    indices = torch.randperm(len(all_strings))[:num_queries]
    query_strings = [all_strings[i.item()] for i in indices]

    queries = get_ffwd_queries(query_strings, encoding_helpers, accessors)
    experiment.run(queries=queries, start_batch_idx=start_batch_idx)
