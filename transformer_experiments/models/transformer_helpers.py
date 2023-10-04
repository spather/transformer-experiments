# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/models/transformer-helpers.ipynb.

# %% auto 0
__all__ = ['EncodingHelpers', 'InputOutputAccessor', 'TransformerAccessors']

# %% ../../nbs/models/transformer-helpers.ipynb 4
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

# %% ../../nbs/models/transformer-helpers.ipynb 5
from fastcore.test import *
import torch

# %% ../../nbs/models/transformer-helpers.ipynb 6
from transformer_experiments.models.transformer import (
    block_size,
    Block,
    n_head,
    n_embed,
    TransformerLanguageModel,
)
from ..tokenizers.char_tokenizer import CharacterTokenizer

# %% ../../nbs/models/transformer-helpers.ipynb 10
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

    def embed_string(self, s: str) -> torch.Tensor:
        """Given a string, performs the token and positional embeddings
        done at the beginning of the model and returns the tensor that
        would be sent into the stack of blocks."""
        return self.embed_tokens(self.tokenize_string(s))

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

# %% ../../nbs/models/transformer-helpers.ipynb 13
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

# %% ../../nbs/models/transformer-helpers.ipynb 14
class TransformerAccessors:
    """Class that provides methods for running pieces of a `TransformerLanguageModel`
    in isolation and introspecting their intermediate results."""

    def __init__(self, m: TransformerLanguageModel):
        self.m = m

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
