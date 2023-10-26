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

# -- Sample Length 4 --
BLOCK_INTERNALS_SLEN4_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen4
BLOCK_INTERNALS_SLEN4_SENTINEL:=$(BLOCK_INTERNALS_SLEN4_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN4_SENTINEL):
	@echo "Generating block internals slen4 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN4_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN4_DIR) \
		--sample_len 4 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN4_SENTINEL)

block_internals_slen4_dataset: $(BLOCK_INTERNALS_SLEN4_SENTINEL)

# -- Sample Length 5 --
BLOCK_INTERNALS_SLEN5_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen5
BLOCK_INTERNALS_SLEN5_SENTINEL:=$(BLOCK_INTERNALS_SLEN5_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN5_SENTINEL):
	@echo "Generating block internals slen5 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN5_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN5_DIR) \
		--sample_len 5 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN5_SENTINEL)

block_internals_slen5_dataset: $(BLOCK_INTERNALS_SLEN5_SENTINEL)

# -- Sample Length 6 --
BLOCK_INTERNALS_SLEN6_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen6
BLOCK_INTERNALS_SLEN6_SENTINEL:=$(BLOCK_INTERNALS_SLEN6_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN6_SENTINEL):
	@echo "Generating block internals slen6 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN6_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN6_DIR) \
		--sample_len 6 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN6_SENTINEL)

block_internals_slen6_dataset: $(BLOCK_INTERNALS_SLEN6_SENTINEL)

# -- Sample Length 7 --
BLOCK_INTERNALS_SLEN7_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen7
BLOCK_INTERNALS_SLEN7_SENTINEL:=$(BLOCK_INTERNALS_SLEN7_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN7_SENTINEL):
	@echo "Generating block internals slen7 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN7_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN7_DIR) \
		--sample_len 7 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN7_SENTINEL)

block_internals_slen7_dataset: $(BLOCK_INTERNALS_SLEN7_SENTINEL)

# -- Sample Length 8 --
BLOCK_INTERNALS_SLEN8_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen8
BLOCK_INTERNALS_SLEN8_SENTINEL:=$(BLOCK_INTERNALS_SLEN8_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN8_SENTINEL):
	@echo "Generating block internals slen8 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN8_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN8_DIR) \
		--sample_len 8 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN8_SENTINEL)

block_internals_slen8_dataset: $(BLOCK_INTERNALS_SLEN8_SENTINEL)

# -- Sample Length 9 --
BLOCK_INTERNALS_SLEN9_DIR:=$(BLOCK_INTERNALS_DATA_DIR)/slen9
BLOCK_INTERNALS_SLEN9_SENTINEL:=$(BLOCK_INTERNALS_SLEN9_DIR)/__data_generated

$(BLOCK_INTERNALS_SLEN9_SENTINEL):
	@echo "Generating block internals slen9 data set"
	@mkdir -p $(BLOCK_INTERNALS_SLEN9_DIR)
	block_internals_exp_run \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(BLOCK_INTERNALS_SLEN9_DIR) \
		--sample_len 9 \
		--max_batch_size 10000
	@touch $(BLOCK_INTERNALS_SLEN9_SENTINEL)

block_internals_slen9_dataset: $(BLOCK_INTERNALS_SLEN9_SENTINEL)

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

# ====== Similar Strings ======
SIMILAR_STRINGS_SLEN10_DIR:=$(BLOCK_INTERNALS_SLEN10_DIR)/similar_strings

similar_strings_slen10_all: similar_strings_slen10_map similar_strings_slen10_embeddings similar_strings_slen10_proj_outputs similar_strings_slen10_ffwd_outputs

# -- String to batch map --
SIMILAR_STRINGS_SLEN10_MAP_SENTINEL:=$(SIMILAR_STRINGS_SLEN10_DIR)/__map_data_generated
$(SIMILAR_STRINGS_SLEN10_MAP_SENTINEL):
	@echo "Generating strings to batch map"
	@mkdir -p $(SIMILAR_STRINGS_SLEN10_DIR)
	similar_strings_exp_run \
		--batch_size 100 \
		--sample_len 10 \
		--random_seed 1337 \
		--n_samples 20000 \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(SIMILAR_STRINGS_SLEN10_DIR) \
		generate-string-to-batch-map
	@touch $(SIMILAR_STRINGS_SLEN10_MAP_SENTINEL)

similar_strings_slen10_map: $(SIMILAR_STRINGS_SLEN10_MAP_SENTINEL)

# -- Embeddings --
SIMILAR_STRINGS_SLEN10_EMBEDDINGS_SENTINEL:=$(SIMILAR_STRINGS_SLEN10_DIR)/__embeddings_data_generated
$(SIMILAR_STRINGS_SLEN10_EMBEDDINGS_SENTINEL):
	@echo "Generating embeddings"
	@mkdir -p $(SIMILAR_STRINGS_SLEN10_DIR)
	similar_strings_exp_run \
		--batch_size 100 \
		--sample_len 10 \
		--random_seed 1337 \
		--n_samples 20000 \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(SIMILAR_STRINGS_SLEN10_DIR) \
		generate-similars \
		--block_internals_experiment_output_folder $(BLOCK_INTERNALS_SLEN10_DIR) \
		--block_internals_experiment_max_batch_size 10000 \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		embeddings
	@touch $(SIMILAR_STRINGS_SLEN10_EMBEDDINGS_SENTINEL)

similar_strings_slen10_embeddings: $(SIMILAR_STRINGS_SLEN10_EMBEDDINGS_SENTINEL)

# -- Proj Outputs --
T_INDICES := 4 5 9

similar_strings_slen10_proj_outputs: $(patsubst %, similar_strings_slen10_proj_outputs_%, $(T_INDICES))

$(patsubst %, similar_strings_slen10_proj_outputs_%, $(T_INDICES)): similar_strings_slen10_proj_outputs_%: $(SIMILAR_STRINGS_SLEN10_DIR)/__proj_outputs_data_generated_t%

similar_strings_slen10_proj_outputs_%: T_INDEX=$*

$(SIMILAR_STRINGS_SLEN10_DIR)/__proj_outputs_data_generated_t%:
	@echo "Generating proj outputs for t_index=$(T_INDEX)"
	@mkdir -p $(SIMILAR_STRINGS_SLEN10_DIR)
	similar_strings_exp_run \
		--batch_size 100 \
		--sample_len 10 \
		--random_seed 1337 \
		--n_samples 20000 \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(SIMILAR_STRINGS_SLEN10_DIR) \
		generate-similars \
		--block_internals_experiment_output_folder $(BLOCK_INTERNALS_SLEN10_DIR) \
		--block_internals_experiment_max_batch_size 10000 \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		proj-out \
		--t_index $(T_INDEX)
	@touch $@

# -- FFWD Outputs --
similar_strings_slen10_ffwd_outputs: $(patsubst %, similar_strings_slen10_ffwd_outputs_%, $(T_INDICES))

$(patsubst %, similar_strings_slen10_ffwd_outputs_%, $(T_INDICES)): similar_strings_slen10_ffwd_outputs_%: $(SIMILAR_STRINGS_SLEN10_DIR)/__ffwd_outputs_data_generated_t%

similar_strings_slen10_ffwd_outputs_%: T_INDEX=$*

$(SIMILAR_STRINGS_SLEN10_DIR)/__ffwd_outputs_data_generated_t%:
	@echo "Generating ffwd outputs for t_index=$(T_INDEX)"
	@mkdir -p $(SIMILAR_STRINGS_SLEN10_DIR)
	similar_strings_exp_run \
		--batch_size 100 \
		--sample_len 10 \
		--random_seed 1337 \
		--n_samples 20000 \
		$(ROOT_DIR)/nbs/artifacts/input.txt \
		$(SIMILAR_STRINGS_SLEN10_DIR) \
		generate-similars \
		--block_internals_experiment_output_folder $(BLOCK_INTERNALS_SLEN10_DIR) \
		--block_internals_experiment_max_batch_size 10000 \
		$(ROOT_DIR)/nbs/artifacts/shakespeare.pt \
		ffwd-out \
		--t_index $(T_INDEX)
	@touch $@
