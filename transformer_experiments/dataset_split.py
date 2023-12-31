# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/training/dataset-split.ipynb.

# %% auto 0
__all__ = ['split_text_dataset']

# %% ../nbs/training/dataset-split.ipynb 4
from typing import Tuple

# %% ../nbs/training/dataset-split.ipynb 5
import torch

# %% ../nbs/training/dataset-split.ipynb 6
from transformer_experiments.tokenizers.char_tokenizer import (
    CharacterTokenizer,
)

# %% ../nbs/training/dataset-split.ipynb 7
def split_text_dataset(
    text: str, tokenizer: CharacterTokenizer, train_pct: float, device: str
) -> Tuple[torch.Tensor, torch.Tensor]:
    data = torch.tensor(tokenizer.encode(text), dtype=torch.long, device=device)
    n = int(train_pct * len(data))
    train_data = data[:n]
    val_data = data[n:]
    return train_data, val_data
