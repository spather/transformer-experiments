# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/common/environments.ipynb.

# %% auto 0
__all__ = ['Environment', 'get_environment']

# %% ../nbs/common/environments.ipynb 2
from dataclasses import dataclass
import os
import platform
from pathlib import Path

# %% ../nbs/common/environments.ipynb 5
@dataclass
class Environment:
    name: str
    code_root: Path
    data_root: Path

# %% ../nbs/common/environments.ipynb 6
# Heuristics that determine the environment. These are not perfect,
# but they do the job for now.
def is_running_on_local_mac():
    return platform.system() == "Darwin"


def is_running_in_paperspace():
    return "PAPERSPACE_FQDN" in os.environ


def is_running_in_github_actions():
    return "GITHUB_ACTIONS" in os.environ

# %% ../nbs/common/environments.ipynb 7
def get_environment() -> Environment:
    if is_running_on_local_mac():
        data_root = Path("../../generated_data")
        data_root.mkdir(exist_ok=True)
        return Environment(
            name="local_mac",
            code_root=Path("../../").resolve(),
            data_root=data_root.resolve(),
        )
    elif is_running_in_paperspace():
        return Environment(
            name="paperspace",
            code_root=Path("/notebooks/code/transformer-experiments/"),
            data_root=Path("/storage/"),
        )
    elif is_running_in_github_actions():
        data_root = Path(
            "/home/runner/work/transformer-experiments/transformer-experiments/generated_data"
        )
        data_root.mkdir(exist_ok=True)
        return Environment(
            name="github_actions",
            code_root=Path(
                "/home/runner/work/transformer-experiments/transformer-experiments/"
            ),
            data_root=data_root,
        )
    else:
        raise ValueError("Unknown environment")
