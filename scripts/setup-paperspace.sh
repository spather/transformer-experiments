#!/usr/bin/env bash
set -euo pipefail

# check for the existince of the PAPERSPACE_FQDN environment variable
# as a heuristic for determining whether this script is being run on
# a paperspace machine.
if [ -z "${PAPERSPACE_FQDN:-}" ]; then
  echo "Error: PAPERSPACE_FQDN is not set -- are you running this on a PaperSpace machine?"
  exit 1
fi

# Get the directory in which this script lives
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get the repo root directory
ROOT=$(cd "${DIR}/../" && pwd)

# The paperspace notebooks directory (not the nbs directory in the repo)
NOTEBOOKS="/notebooks"

# install manim deps
sudo apt update
sudo apt install build-essential python3-dev libcairo2-dev libpango1.0-dev ffmpeg

# create and activate venv
VENV_DIR="${NOTEBOOKS}/venv/venv-transformer"
mkdir -p "${VENV_DIR}"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

# install requirements
pip install -r "${ROOT}/requirements.linux.txt"
pip install -r "${ROOT}/requirements.dev.linux.txt"

# install this project's package
pip install -e '${ROOT}[dev]'

# install ipykernel
python3 -m ipykernel install --user --name transformer-experiments --display-name "Python (transformer-experiments)"

# install and set up git-lfs
sudo apt-get install git-lfs
(
  cd "${ROOT}"
  git lfs install
  git lfs pull --include "${ROOT}/nbs/artifacts/shakespeare-20231112.pt"
)

