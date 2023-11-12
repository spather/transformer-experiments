# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/training/training-utils.ipynb.

# %% auto 0
__all__ = ['TModel', 'CheckPointer', 'EstimateLossFunction', 'GetBatchFunction', 'OnBatchTrainedHandler',
           'OnCheckpointSavedHandler', 'Trainer']

# %% ../nbs/training/training-utils.ipynb 2
from pathlib import Path
import tempfile
from typing import Dict, Generic, List, Protocol, Tuple, TypeVar

# %% ../nbs/training/training-utils.ipynb 3
import torch
from tqdm.auto import tqdm

# %% ../nbs/training/training-utils.ipynb 6
class CheckPointer:
    def __init__(self, output_dir: Path, filename_stem: str, start_num: int = 0):
        self.output_dir = output_dir
        self.filename_stem = filename_stem
        self.num = start_num

    def filename(self):
        return self.output_dir / f"{self.filename_stem}_{self.num:06d}.pt"

    def save_checkpoint(
        self, iters: int, model: torch.nn.Module, train_loss: float, val_loss: float
    ) -> Path:
        filename = self.filename()
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "iters": iters,
                "train_loss": train_loss,
                "val_loss": val_loss,
            },
            filename,
        )
        self.num += 1
        return filename

# %% ../nbs/training/training-utils.ipynb 8
TModel = TypeVar("TModel", bound=torch.nn.Module, contravariant=True)


class EstimateLossFunction(Protocol[TModel]):
    def __call__(self, model: TModel) -> Dict[str, float]:
        ...


class GetBatchFunction(Protocol):
    def __call__(self, split: str) -> Tuple[torch.Tensor, torch.Tensor]:
        ...


class OnBatchTrainedHandler(Protocol):
    def __call__(self, iters_trained: int, batch: torch.Tensor) -> None:
        ...


class OnCheckpointSavedHandler(Protocol):
    def __call__(self, iters_trained: int, checkpoint_file: Path) -> None:
        ...


class Trainer(Generic[TModel]):
    def __init__(
        self,
        model: TModel,
        checkpointer: CheckPointer,
        get_batch_func: GetBatchFunction,
        estimate_loss_func: EstimateLossFunction[TModel],
        iters_trained: int = 0,
    ):
        self.model = model
        self.checkpointer = checkpointer
        self.get_batch_func = get_batch_func
        self.estimate_loss_func = estimate_loss_func
        self.iters_trained = iters_trained
        self.on_batch_trained_handlers: List[OnBatchTrainedHandler] = []
        self.on_checkpoint_saved_handlers: List[OnCheckpointSavedHandler] = []

    def add_on_batch_trained_handler(self, handler: OnBatchTrainedHandler):
        self.on_batch_trained_handlers.append(handler)

    def add_on_checkpoint_saved_handler(self, handler: OnCheckpointSavedHandler):
        self.on_checkpoint_saved_handlers.append(handler)

    def fire_on_batch_trained(self, batch: torch.Tensor):
        for handler in self.on_batch_trained_handlers:
            handler(self.iters_trained, batch)

    def fire_on_checkpoint_saved(self, checkpoint_file: Path):
        for handler in self.on_checkpoint_saved_handlers:
            handler(self.iters_trained, checkpoint_file)

    def train(
        self,
        n_iters: int,
        optimizer: torch.optim.Optimizer,
        eval_interval: int = 500,
        disable_progress_bar: bool = False,
        disable_output: bool = False,
    ):
        self.model.train()
        for steps in tqdm(range(n_iters), disable=disable_progress_bar):
            xb, yb = self.get_batch_func(split="train")

            _, loss = self.model(xb, yb)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            self.iters_trained += 1
            self.fire_on_batch_trained(xb)

            if self.iters_trained % eval_interval == 0:
                losses = self.estimate_loss_func(self.model)
                if not disable_output:
                    print(
                        f"step {steps}: train loss {losses['train']:.4f}, val loss {losses['val']:.4f}"
                    )
                checkpoint_filename = self.checkpointer.save_checkpoint(
                    self.iters_trained,
                    self.model,
                    losses["train"],
                    losses["val"],
                )
                self.fire_on_checkpoint_saved(checkpoint_filename)
