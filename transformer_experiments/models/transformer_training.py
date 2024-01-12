# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/models/transformer-training.ipynb.

# %% auto 0
__all__ = ['batch_size', 'eval_interval', 'eval_iters', 'estimate_loss']

# %% ../../nbs/models/transformer-training.ipynb 5
import torch

from .transformer import TransformerLanguageModel
from ..training_utils import GetBatchFunction

# For now, there's nothing defined in this module, besides imports.
# However, some cells in ./transformer.ipynb export to the module
# defined by this notebook. The imports here are the imports needed
# by the code in those cells.
#
# Nbdev requires a dedicated notebook to create a module. For historical
# reasons, the code actually lives in the transformer notebook and it seems
# like unnecessary work to move it here.

# %% ../../nbs/models/transformer.ipynb 23
@torch.no_grad()
def estimate_loss(
    model: TransformerLanguageModel, eval_iters: int, get_batch_func: GetBatchFunction
):
    out = {}
    model.eval()  # Put the model into eval mode (e.g. turn off things like dropout etc.)
    for split in ["train", "val"]:
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            X, Y = get_batch_func(split=split)
            _, loss = model(X, Y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    model.train()  # Put the model back into training mode so things like dropout happen
    return out

# %% ../../nbs/models/transformer.ipynb 26
batch_size = 64  # how many independent sequences will we process in parallel?

eval_interval = 500
eval_iters = 200