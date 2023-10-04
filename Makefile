all: prepare clean_old mypy

export_lib:
	nbdev_export

# Prepare bundles export_lib, test, clean, and readme
prepare:
	nbdev_prepare

mypy:
	mypy transformer_experiments/

test:
	nbdev_test

clean:
	nbdev_clean

clean_old:
	find nbs/_old -name '_*.ipynb' -exec nbdev_clean --fname {} \;

readme:
	nbdev_readme

# Get the root directory of the project (the directory where this Makefile lives)
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Define the library dir relative to the root dir. This is so that it's always
# correct even if this makefile somehow got invoked from another directory.
LIB_DIR:=$(ROOT_DIR)/transformer_experiments

clean_lib_dir:
	@echo Cleaning $(LIB_DIR)
	rm -rf $(LIB_DIR)