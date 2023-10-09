# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/models/transformer-helpers.ipynb.

# %% auto 0
__all__ = ['EncodingHelpers', 'InputOutputAccessor', 'TransformerAccessors', 'LogitsWrapper']

# %% ../../nbs/models/transformer-helpers.ipynb 5
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

# %% ../../nbs/models/transformer-helpers.ipynb 6
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np
import torch
import torch.nn as nn
from torch.nn import functional as F

# %% ../../nbs/models/transformer-helpers.ipynb 7
from transformer_experiments.models.transformer import (
    block_size,
    Block,
    n_head,
    n_embed,
    n_layer,
    TransformerLanguageModel,
)
from ..tokenizers.char_tokenizer import CharacterTokenizer

# %% ../../nbs/models/transformer-helpers.ipynb 11
class EncodingHelpers:
    def __init__(
        self, m: TransformerLanguageModel, tokenizer: CharacterTokenizer, device: str
    ):
        self.m = m
        self.tokenizer = tokenizer
        self.device = device

    def tokenize_string(self, s: str) -> torch.Tensor:
        """Given a string, returns a tensor representing the tokenized string.
        The returned tensor has shape (1, T) where T is the number of tokens,
        so it works in situations that expect a batch dimension."""
        return torch.tensor(
            [self.tokenizer.encode(s)], dtype=torch.long, device=self.device
        )

    def stringify_tokens(self, tokens: torch.Tensor) -> str:
        """Given a tensor of tokens, returns a string representing the tokens."""
        return self.tokenizer.decode(tokens.tolist())

    def unsqueeze_emb(
        self, emb: torch.Tensor, expected_last_dim_size: int = n_embed
    ) -> torch.Tensor:
        """A lot of things expect embedding tensors to have shape (B, T, X) where
        X is usually either n_embed or vocab_size. This function takes an embedding
        tensor that may be missing some of these dimensions and adds them as
        necessary."""
        ndim = emb.ndim
        if ndim > 3:
            raise ValueError(f"Expected embedding tensor to have ndim <= 3, got {ndim}")

        if emb.shape[-1] != expected_last_dim_size:
            raise ValueError(
                f"Expected embedding tensor to have last dimension {expected_last_dim_size}, got {emb.shape[-1]}"
            )

        if ndim == 1:
            return emb.unsqueeze(0).unsqueeze(0)
        elif ndim == 2:
            return emb.unsqueeze(0)

        return emb  # ndim == 3, nothing to change

# %% ../../nbs/models/transformer-helpers.ipynb 15
class InputOutputAccessor:
    def __init__(self, activations: Dict[str, Tuple]):
        self.activations = activations

    def inputs(self, name: str) -> Tuple[torch.Tensor]:
        return self.activations[name][0]

    def input(self, name: str) -> torch.Tensor:
        inps = self.inputs(name)
        assert len(inps) == 1
        return inps[0]

    def output(self, name: str) -> torch.Tensor:
        return self.activations[name][1]

# %% ../../nbs/models/transformer-helpers.ipynb 16
class TransformerAccessors:
    """Class that provides methods for running pieces of a `TransformerLanguageModel`
    in isolation and introspecting their intermediate results."""

    def __init__(self, m: TransformerLanguageModel, device: str):
        self.m = m
        self.device = device

    def embed_tokens(self, tokens: torch.Tensor) -> torch.Tensor:
        """Given a tensor of tokens containing a batch of tokens (shape B, T),
        performs the token and positional embeddings done at the beginning of
        the model and returns the tensor that would be sent into the stack of
        blocks."""
        idx = tokens[:, -block_size:]

        # Logic from the model's forward() function
        B, T = idx.shape
        token_emb = self.m.token_embedding_table(idx)
        pos_emb = self.m.position_embedding_table(
            torch.arange(T, device=self.device)
        )  # (T, n_embed)
        x = token_emb + pos_emb
        return x.detach()

    def copy_block_from_model(self, block_idx: int):
        """Given the index of a block in the model [0, n_layer), creates
        a new block with identical parameters.

        Returns
        -------
        Tuple
            First element is the new block, second is an `InputOutputAccessor` that
            provides access to the inputs and outputs of the block itself, it top-level
            sub-modules, and children of the self-attention sub-module.
        """
        block = self.m.blocks[block_idx]
        new_block = Block(n_embed, n_head)
        new_block.load_state_dict(block.state_dict())
        new_block.eval()

        activations = {}

        def log_activation_hook(name):
            def hook(_, input, output):
                inputs = tuple([inp.detach() for inp in input])
                activations[name] = (inputs, output.detach())

            return hook

        new_block.register_forward_hook(log_activation_hook("."))
        for name, module in new_block.named_children():
            module.register_forward_hook(log_activation_hook(name))

        # Register the hook for the self-attention layer's children as
        # I will need this. Wanted this function to not have to know
        # about the internal structure of a block (i.e. not access members
        # by a specific name), so this is unfortunate, but the most expedient.
        for name, module in new_block.sa.named_children():
            module.register_forward_hook(log_activation_hook(f"sa.{name}"))

        return new_block, InputOutputAccessor(activations)

    def check_valid_input_shape(self, emb):
        if emb.ndim != 3:
            raise ValueError(
                f"Expected embedding tensor to have ndim 3, got {emb.ndim}"
            )

        if emb.shape[-1] != n_embed:
            raise ValueError(
                f"Expected embedding tensor to have last dimension {n_embed}, got {emb.shape[-1]}"
            )

    def logits_from_embedding(self, emb: torch.Tensor) -> torch.Tensor:
        """Given embeddings, returns the logits that would be
        generated by the model."""
        x = self.m.ln_f(emb)
        logits = self.m.lm_head(x)

        return logits.detach()

    def run_model(
        self, embedded_input: torch.Tensor
    ) -> Tuple[torch.Tensor, Sequence[InputOutputAccessor]]:
        """Given an input (already embedded), runs the model on it and returns a
        the logits and a sequence of `InputOutputAccessor` objects that provide
        access to the inputs and outputs of each block in the model."""
        self.check_valid_input_shape(embedded_input)

        blocks, io_accessors = zip(
            *[  # See https://stackoverflow.com/a/13635074
                self.copy_block_from_model(block_idx=i) for i in range(n_layer)
            ]
        )

        blocks_module = nn.Sequential(*blocks)

        x = blocks_module(embedded_input)
        logits = self.logits_from_embedding(x)

        return logits.detach(), io_accessors

# %% ../../nbs/models/transformer-helpers.ipynb 22
class LogitsWrapper:
    """A wrapper class around a tensor of logits that provides
    convenience methods for interpreting and visualizing them."""

    def __init__(self, logits: torch.Tensor, tokenizer: CharacterTokenizer):
        # For consistency, we always want logits to be of shape (B, T, vocab_size).
        # It's up to the calling code to add the B and T dimensions if necessary.
        assert logits.dim() == 3
        _, _, vocab_size = logits.shape
        assert vocab_size == tokenizer.vocab_size

        self.logits = logits
        self.tokenizer = tokenizer

    def probs(self) -> torch.Tensor:
        return F.softmax(self.logits, dim=-1)

    def topk_tokens(self, k: int) -> Sequence[Sequence[Sequence[Tuple[str, float]]]]:
        """Returns the top k tokens and their probabilities."""
        probs = self.probs()
        _, topk_indices = torch.topk(probs, k=k, dim=-1)

        B, T, _ = self.logits.shape
        top_tokens = [
            [
                [
                    (self.tokenizer.itos[i], probs[b_i, t_i, i].item())
                    for i in topk_indices[b_i, t_i].tolist()
                ]
                for t_i in range(T)
            ]
            for b_i in range(B)
        ]

        return top_tokens

    def plot_probs(
        self,
        b_i: int = 0,
        t_i: int = -1,
        title: str = "",
        ax: Optional[Axes] = None,
        figsize=(12, 4),
    ):
        """Plots the output probabilities for each token based on the logits"""
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)

        x_indices = np.arange(self.tokenizer.vocab_size)
        x_labels = [repr(c)[1:-1] for c in self.tokenizer.chars]

        ax.bar(x_indices, self.probs()[b_i, t_i])
        ax.set_xticks(x_indices, x_labels, rotation="vertical")
        ax.set_title(title)
        ax.set_ylim(0.0, 1.0)
