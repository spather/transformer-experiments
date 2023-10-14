.PHONY: all export_lib prepare mypy test clean clean_old clean_templates \
	readme clean_lib_dir no_fastcore_import_in_lib

all: prepare no_fastcore_import_in_lib clean_old clean_templates mypy

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

clean_templates:
	find nbs/_templates -name '_*.ipynb' -exec nbdev_clean --fname {} \;

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

# Check that 'fastcore.test' is not imported in the library. It should
# only be imported in the notebooks.
no_fastcore_import_in_lib:
	@echo "Checking for fastcore imports in $(LIB_DIR)"
	@output=$$(find $(LIB_DIR) -name '*.py' -exec grep -nH 'from fastcore.test import' {} \;) ;\
	if [ "$$output" ]; then \
		echo "Detected unwanted imports of fastcore.test in library:" ;\
		echo "$$output" ;\
		exit 1 ;\
	fi

# Data Sets

# ====== Block Internals ======
BLOCK_INTERNALS_DATA_DIR:=$(ROOT_DIR)/nbs/artifacts/block_internals_results/large_files

# -- Sample Length 3 --
BLOCK_INTERNALS_SLEN3_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen3
BLOCK_INTERNALS_SLEN3_SENTINEL:=$(BLOCK_INTERNALS_SLEN3_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN3_SENTINEL):
	@echo "Generating block internals slen3 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN3_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN3_DIR) \
		--sample_len 3 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN3_SENTINEL)

block_internals_slen3_dataset: $(BLOCK_INTERNALS_SLEN3_SENTINEL)

# -- Sample Length 10 --
BLOCK_INTERNALS_SLEN10_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen10
BLOCK_INTERNALS_SLEN10_SENTINEL:=$(BLOCK_INTERNALS_SLEN10_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN10_SENTINEL):
	@echo "Generating block internals slen10 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN10_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN10_DIR) \
		--sample_len 10 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN10_SENTINEL)

block_internals_slen10_dataset: $(BLOCK_INTERNALS_SLEN10_SENTINEL)
