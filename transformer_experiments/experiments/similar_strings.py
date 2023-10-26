# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/experiments/similar-strings.ipynb.

# %% auto 0
__all__ = ['SimilarStringsData', 'SimilarStringsResult', 'SimilarStringsExperiment', 'run', 'generate_string_to_batch_map',
           'generate_similars', 'embeddings', 'proj_out', 'ffwd_out']

# %% ../../nbs/experiments/similar-strings.ipynb 5
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import tempfile
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# %% ../../nbs/experiments/similar-strings.ipynb 6
import click
import torch
from tqdm.auto import tqdm

# %% ../../nbs/experiments/similar-strings.ipynb 7
from ..common.substring_generator import all_unique_substrings
from transformer_experiments.datasets.tinyshakespeare import (
    TinyShakespeareDataSet,
)
from transformer_experiments.experiments.block_internals import (
    BlockInternalsExperiment,
    BatchedBlockInternalsExperiment,
)
from transformer_experiments.models.transformer import (
    block_size,
    n_layer,
    TransformerLanguageModel,
)
from transformer_experiments.models.transformer_helpers import (
    EncodingHelpers,
    TransformerAccessors,
)
from ..tokenizers.char_tokenizer import CharacterTokenizer
from transformer_experiments.trained_models.tinyshakespeare_transformer import (
    create_model_and_tokenizer,
)

# %% ../../nbs/experiments/similar-strings.ipynb 10
@dataclass
class SimilarStringsData:
    sim_strings: Sequence[str]
    distances: torch.Tensor


@dataclass
class SimilarStringsResult:
    s: str
    embs: SimilarStringsData
    # proj_out and ffw_out are lists of dicts. One dict per block. Each dict
    # maps a particular t_i to the data from that t_i.
    proj_out: List[Dict[int, SimilarStringsData]] = field(
        default_factory=lambda: [{} for _ in range(n_layer)]
    )
    ffwd_out: List[Dict[int, SimilarStringsData]] = field(
        default_factory=lambda: [{} for _ in range(n_layer)]
    )

# %% ../../nbs/experiments/similar-strings.ipynb 11
class SimilarStringsExperiment:
    def __init__(
        self,
        output_dir: Path,
        encoding_helpers: EncodingHelpers,
    ):
        self.output_dir = output_dir
        self.encoding_helpers = encoding_helpers
        self.string_to_batch_map: Optional[Dict[str, int]] = None

    def _string_to_batch_map_filename(self) -> Path:
        return self.output_dir / "string_to_batch_map.json"

    def _embs_sim_strings_filename(self, batch_idx: int) -> Path:
        return self.output_dir / f"embs_sim_strings-{batch_idx:03d}.json"

    def _proj_out_sim_strings_filename(
        self, batch_idx: int, block_idx: int, t_i: int
    ) -> Path:
        return (
            self.output_dir
            / f"proj_out_sim_strings-{batch_idx:03d}-{block_idx:02d}-{t_i:03d}.json"
        )

    def _ffwd_out_sim_strings_filename(
        self, batch_idx: int, block_idx: int, t_i: int
    ) -> Path:
        return (
            self.output_dir
            / f"ffwd_out_sim_strings-{batch_idx:03d}-{block_idx:02d}-{t_i:03d}.json"
        )

    def generate_string_to_batch_map(
        self,
        strings: Sequence[str],
        batch_size: int = 100,
        disable_progress_bars: bool = False,
    ):
        n_batches = math.ceil(len(strings) / batch_size)

        string_to_batch_map: Dict[str, int] = {}

        for batch_idx in tqdm(range(n_batches), disable=disable_progress_bars):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch_strings = strings[start_idx:end_idx]

            for s in batch_strings:
                string_to_batch_map[s] = batch_idx

        self._string_to_batch_map_filename().write_text(
            json.dumps(string_to_batch_map, indent=2)
        )

    def generate_embeddings_files(
        self,
        strings: Sequence[str],
        accessors: TransformerAccessors,
        exp: BatchedBlockInternalsExperiment,
        batch_size: int = 100,
        disable_progress_bars: bool = False,
        n_similars: int = 10,
    ):
        n_batches = math.ceil(len(strings) / batch_size)

        for batch_idx in tqdm(range(n_batches), disable=disable_progress_bars):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch_strings = strings[start_idx:end_idx]

            batch_exp = BlockInternalsExperiment(
                self.encoding_helpers, accessors, batch_strings
            )

            # Compute the embedding similar strings
            sim_strings, distances = exp.strings_with_topk_closest_embeddings(
                queries=batch_exp.embeddings, k=n_similars, largest=False
            )

            self._embs_sim_strings_filename(batch_idx).write_text(
                json.dumps(
                    {
                        "strings": {s: i for i, s in enumerate(batch_strings)},
                        "sim_strings": sim_strings,
                        "distances": distances.tolist(),
                    },
                    indent=2,
                )
            )

    def generate_proj_out_files(
        self,
        strings: Sequence[str],
        t_i: int,
        accessors: TransformerAccessors,
        exp: BatchedBlockInternalsExperiment,
        batch_size: int = 100,
        disable_progress_bars: bool = False,
        n_similars: int = 10,
    ):
        filename_t_i = t_i
        if filename_t_i < 0:
            filename_t_i = exp.sample_length() + filename_t_i
        assert filename_t_i >= 0, f"converted t_i must be >= 0, was {filename_t_i}"

        n_batches = math.ceil(len(strings) / batch_size)

        for batch_idx in tqdm(range(n_batches), disable=disable_progress_bars):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch_strings = strings[start_idx:end_idx]

            batch_exp = BlockInternalsExperiment(
                self.encoding_helpers, accessors, batch_strings
            )

            for block_idx in range(n_layer):
                # Compute the proj_out similar strings
                sim_strings, distances = exp.strings_with_topk_closest_proj_outputs(
                    block_idx=block_idx,
                    t_i=t_i,
                    # Query is always the last token - for something else, use a shorter string
                    queries=batch_exp.proj_output(block_idx)[:, -1, :],
                    k=n_similars,
                    largest=False,
                )
                self._proj_out_sim_strings_filename(
                    batch_idx, block_idx, filename_t_i
                ).write_text(
                    json.dumps(
                        {
                            "strings": {s: i for i, s in enumerate(batch_strings)},
                            "sim_strings": sim_strings,
                            "distances": distances.tolist(),
                        },
                        indent=2,
                    )
                )

    def generate_ffwd_out_files(
        self,
        strings: Sequence[str],
        t_i: int,
        accessors: TransformerAccessors,
        exp: BatchedBlockInternalsExperiment,
        batch_size: int = 100,
        disable_progress_bars: bool = False,
        n_similars: int = 10,
    ):
        n_batches = math.ceil(len(strings) / batch_size)

        filename_t_i = t_i
        if filename_t_i < 0:
            filename_t_i = exp.sample_length() + filename_t_i
        assert filename_t_i >= 0, f"converted t_i must be >= 0, was {filename_t_i}"

        for batch_idx in tqdm(range(n_batches), disable=disable_progress_bars):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch_strings = strings[start_idx:end_idx]

            batch_exp = BlockInternalsExperiment(
                self.encoding_helpers, accessors, batch_strings
            )

            for block_idx in range(n_layer):
                sim_strings, distances = exp.strings_with_topk_closest_ffwd_outputs(
                    block_idx=block_idx,
                    t_i=t_i,
                    # Query is always the last token - for something else, use a shorter string
                    queries=batch_exp.ffwd_output(block_idx)[:, -1, :],
                    k=n_similars,
                    largest=False,
                )

                self._ffwd_out_sim_strings_filename(
                    batch_idx, block_idx, filename_t_i
                ).write_text(
                    json.dumps(
                        {
                            "strings": {s: i for i, s in enumerate(batch_strings)},
                            "sim_strings": sim_strings,
                            "distances": distances.tolist(),
                        },
                        indent=2,
                    )
                )

    def _load_json(self, file: Path):
        return json.loads(file.read_text())

    def load_string_to_batch_map(self):
        if self.string_to_batch_map is not None:
            return

        self.string_to_batch_map = self._load_json(self._string_to_batch_map_filename())

    def load_results_for_strings(
        self, strings: Sequence[str], load_t_is: Sequence[int] = [-1]
    ):
        self.load_string_to_batch_map()
        assert self.string_to_batch_map is not None

        sample_len = len(next(iter(self.string_to_batch_map.keys())))
        # Convert any negative t_is to positive.
        load_t_is = [t_i if t_i >= 0 else sample_len + t_i for t_i in load_t_is]

        assert all(
            0 <= t_i < sample_len for t_i in load_t_is
        ), f"all t_is must be in [0, {sample_len}), were {load_t_is}"

        batch_to_strings: Dict[int, List[str]] = defaultdict(list)
        for s in strings:
            batch_idx = self.string_to_batch_map[s]
            batch_to_strings[batch_idx].append(s)

        string_to_results: Dict[str, SimilarStringsResult] = {}
        for batch_idx, strings in batch_to_strings.items():
            emb_batch = self._load_json(self._embs_sim_strings_filename(batch_idx))
            emb_distances = torch.tensor(emb_batch["distances"], dtype=torch.float32)

            for s in strings:
                s_idx = emb_batch["strings"][s]
                sim_strings = emb_batch["sim_strings"][s_idx]
                distances = emb_distances[:, s_idx]

                emb_data = SimilarStringsData(sim_strings, distances)
                string_to_results[s] = SimilarStringsResult(s, emb_data)

            for block_idx in range(n_layer):
                for t_i in load_t_is:
                    proj_batch = self._load_json(
                        self._proj_out_sim_strings_filename(
                            batch_idx=batch_idx, block_idx=block_idx, t_i=t_i
                        )
                    )
                    proj_distances = torch.tensor(
                        proj_batch["distances"], dtype=torch.float32
                    )

                    for s in strings:
                        s_idx = proj_batch["strings"][s]
                        sim_strings = proj_batch["sim_strings"][s_idx]
                        distances = proj_distances[:, s_idx]
                        string_to_results[s].proj_out[block_idx][
                            t_i
                        ] = SimilarStringsData(sim_strings, distances)

                    ffwd_batch = self._load_json(
                        self._ffwd_out_sim_strings_filename(
                            batch_idx=batch_idx, block_idx=block_idx, t_i=t_i
                        )
                    )
                    ffwd_distances = torch.tensor(
                        ffwd_batch["distances"], dtype=torch.float32
                    )

                    for s in strings:
                        s_idx = ffwd_batch["strings"][s]
                        sim_strings = ffwd_batch["sim_strings"][s_idx]
                        distances = ffwd_distances[:, s_idx]
                        string_to_results[s].ffwd_out[block_idx][
                            t_i
                        ] = SimilarStringsData(sim_strings, distances)

        return string_to_results

# %% ../../nbs/experiments/similar-strings.ipynb 14
# CLI for generating similar strings files
@click.group()
@click.argument("dataset_cache_filename", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=True))
@click.option(
    "-b",
    "--batch_size",
    required=False,
    type=click.IntRange(min=1),
    default=100,
)
@click.option(
    "-s",
    "--sample_len",
    required=True,
    type=click.IntRange(min=1, max=block_size),
)
@click.option(
    "-r",
    "--random_seed",
    required=True,
    type=click.INT,
)
@click.option(
    "--n_samples",
    required=True,
    type=click.IntRange(min=1),
)
@click.pass_context
def run(
    ctx: click.Context,
    dataset_cache_filename: str,
    output_folder: str,
    sample_len: int,
    n_samples: int,
    random_seed: int,
    batch_size: int,
):
    ctx.ensure_object(dict)

    click.echo("SimilarStringsExperiment CLI")
    click.echo()
    click.echo(f"  dataset cache: {dataset_cache_filename}")
    click.echo(f"  output folder: {output_folder}")

    click.echo()
    click.echo(f"  sample length: {sample_len}")
    click.echo(f"  n samples: {n_samples}")
    click.echo(f"  random seed: {random_seed}")

    click.echo()
    click.echo(f"  batch size: {batch_size}")
    click.echo()

    ctx.obj["batch_size"] = batch_size

    ts = TinyShakespeareDataSet(cache_file=dataset_cache_filename)
    ctx.obj["ts"] = ts

    all_strings = all_unique_substrings(ts.text, sample_len)
    ctx.obj["all_strings"] = all_strings

    torch.manual_seed(random_seed)
    indices = torch.randperm(len(all_strings))[:n_samples]
    strings = [all_strings[i.item()] for i in indices]

    ctx.obj["strings"] = strings

    tokenizer = CharacterTokenizer(text=ts.text)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    click.echo(f"device is {device}")
    ctx.obj["device"] = device

    encoding_helpers = EncodingHelpers(tokenizer, device)

    ss_exp = SimilarStringsExperiment(Path(output_folder), encoding_helpers)
    ctx.obj["ss_exp"] = ss_exp


@run.command()
@click.pass_context
def generate_string_to_batch_map(ctx: click.Context):
    click.echo("Generating string to batch map...")
    click.echo()

    ss_exp = ctx.obj["ss_exp"]
    strings = ctx.obj["strings"]

    ss_exp.generate_string_to_batch_map(strings, batch_size=ctx.obj["batch_size"])

    click.echo(f"Wrote {ss_exp._string_to_batch_map_filename()}")


@run.group()
@click.argument("model_weights_filename", type=click.Path(exists=True))
@click.option(
    "-o",
    "--block_internals_experiment_output_folder",
    required=True,
    type=click.Path(exists=True),
)
@click.option(
    "-m",
    "--block_internals_experiment_max_batch_size",
    required=False,
    type=click.IntRange(min=1),
    default=10000,
)
@click.option(
    "-n",
    "--n_similars",
    required=False,
    type=click.IntRange(min=1),
    default=10,
)
@click.pass_context
def generate_similars(
    ctx: click.Context,
    model_weights_filename: str,
    block_internals_experiment_output_folder: str,
    block_internals_experiment_max_batch_size: int,
    n_similars: int,
):
    click.echo("Generation parameters:")

    click.echo(f"  model weights: {model_weights_filename}")
    click.echo()

    click.echo(
        f"  block internals experiment output folder: {block_internals_experiment_output_folder}"
    )
    click.echo(
        f"  block internals experiment max batch size: {block_internals_experiment_max_batch_size}"
    )
    click.echo()

    click.echo(f"  n similars: {n_similars}")
    click.echo()

    ctx.obj["n_similars"] = n_similars

    # Instantiate the model, tokenizer, and dataset
    device: str = ctx.obj["device"]

    m, tokenizer = create_model_and_tokenizer(
        saved_model_filename=model_weights_filename,
        dataset=ctx.obj["ts"],
        device=device,
    )
    encoding_helpers = EncodingHelpers(tokenizer, device)
    accessors = TransformerAccessors(m, device)
    ctx.obj["accessors"] = accessors

    ctx.obj["exp"] = BatchedBlockInternalsExperiment(
        encoding_helpers,
        accessors,
        ctx.obj["all_strings"],
        output_dir=Path(block_internals_experiment_output_folder),
        batch_size=block_internals_experiment_max_batch_size,
    )


@generate_similars.command()
@click.pass_context
def embeddings(ctx: click.Context):
    click.echo("Generating embeddings similars...")

    ss_exp: SimilarStringsExperiment = ctx.obj["ss_exp"]
    accessors: TransformerAccessors = ctx.obj["accessors"]

    ss_exp.generate_embeddings_files(
        ctx.obj["strings"],
        accessors,
        ctx.obj["exp"],
        batch_size=ctx.obj["batch_size"],
        n_similars=ctx.obj["n_similars"],
    )

    click.echo("Generated embeddings similar strings files.")


@generate_similars.command()
@click.option(
    "-t",
    "--t_index",
    required=True,
    type=click.IntRange(min=0),
)
@click.pass_context
def proj_out(ctx: click.Context, t_index: int):
    click.echo("Generating proj_out similars...")
    click.echo(f"  t_index: {t_index}")

    if t_index >= ctx.obj["exp"].sample_length():
        raise click.BadParameter(
            f"t_index must be less than sample length ({ctx.obj['exp'].sample_length()})",
            param_hint="t_index",
        )

    ss_exp: SimilarStringsExperiment = ctx.obj["ss_exp"]
    accessors: TransformerAccessors = ctx.obj["accessors"]

    ss_exp.generate_proj_out_files(
        ctx.obj["strings"],
        t_index,
        accessors,
        ctx.obj["exp"],
        batch_size=ctx.obj["batch_size"],
        n_similars=ctx.obj["n_similars"],
    )

    click.echo("Generated proj_out similar strings files.")


@generate_similars.command()
@click.option(
    "-t",
    "--t_index",
    required=True,
    type=click.IntRange(min=0),
)
@click.pass_context
def ffwd_out(ctx: click.Context, t_index: int):
    click.echo("Generating ffwd_out similars...")
    click.echo(f"  t_index: {t_index}")

    if t_index >= ctx.obj["exp"].sample_length():
        raise click.BadParameter(
            f"t_index must be less than sample length ({ctx.obj['exp'].sample_length()})",
            param_hint="t_index",
        )

    ss_exp: SimilarStringsExperiment = ctx.obj["ss_exp"]
    accessors: TransformerAccessors = ctx.obj["accessors"]

    ss_exp.generate_ffwd_out_files(
        ctx.obj["strings"],
        t_index,
        accessors,
        ctx.obj["exp"],
        batch_size=ctx.obj["batch_size"],
        n_similars=ctx.obj["n_similars"],
    )

    click.echo("Generated ffwd_out similar strings files.")
