# Makefile for OCI DevOps Tools
# CLI tools for AI-assisted Oracle Cloud Infrastructure operations
# Provides skills and CLI tools for OKE cluster management

CMD_COLOR=\033[1;36m
DESC_COLOR=\033[0;37m
TITLE_COLOR=\033[1;33m
RESET=\033[0m
POLL_SECONDS ?= 30

.PHONY: help install test ssh-sync clean format lint type-check dev-setup ssh-help test-coverage check setup-example quickstart image-updates oke-node-pool-bump oke-node-cycle delete-bucket delete-oke-cluster oke-version-report oke-upgrade oke-upgrade-node-pools

# Default target
help:
	@printf "$(TITLE_COLOR)OCI DevOps Tools - Available Commands$(RESET)\n\n"
	@printf "$(TITLE_COLOR)Setup Commands:$(RESET)\n"
	@printf "  $(CMD_COLOR)install$(RESET)       $(DESC_COLOR)Install dependencies using Poetry$(RESET)\n"
	@printf "  $(CMD_COLOR)dev-setup$(RESET)     $(DESC_COLOR)Complete development setup (install + pre-commit hooks)$(RESET)\n\n"
	@printf "$(TITLE_COLOR)OKE Operations Commands:$(RESET)\n"
	@printf "  $(CMD_COLOR)oke-version-report$(RESET) $(DESC_COLOR)Generate HTML report of OKE cluster and node pool versions$(RESET)\n"
	@printf "  $(CMD_COLOR)oke-upgrade$(RESET)   $(DESC_COLOR)Trigger OKE cluster upgrades using a report file$(RESET)\n"
	@printf "  $(CMD_COLOR)oke-upgrade-node-pools$(RESET) $(DESC_COLOR)Cascade node pool upgrades after the control plane$(RESET)\n"
	@printf "  $(CMD_COLOR)oke-node-cycle$(RESET) $(DESC_COLOR)Cycle node pools to apply new images (boot volume replace)$(RESET)\n"
	@printf "  $(CMD_COLOR)oke-node-pool-bump$(RESET) $(DESC_COLOR)Bump node pool images from CSV report$(RESET)\n\n"
	@printf "$(TITLE_COLOR)SSH Sync Commands:$(RESET)\n"
	@printf "  $(CMD_COLOR)ssh-sync$(RESET)      $(DESC_COLOR)Generate SSH config for OCI instances$(RESET)\n"
	@printf "  $(CMD_COLOR)ssh-help$(RESET)      $(DESC_COLOR)Show SSH sync configuration help$(RESET)\n"
	@printf "  $(CMD_COLOR)image-updates$(RESET) $(DESC_COLOR)Check for newer images for compute instances$(RESET)\n\n"
	@printf "$(TITLE_COLOR)Resource Management:$(RESET)\n"
	@printf "  $(CMD_COLOR)delete-bucket$(RESET) $(DESC_COLOR)Delete an OCI bucket$(RESET)\n"
	@printf "  $(CMD_COLOR)delete-oke-cluster$(RESET) $(DESC_COLOR)Delete an OKE cluster$(RESET)\n\n"
	@printf "$(TITLE_COLOR)Development Commands:$(RESET)\n"
	@printf "  $(CMD_COLOR)test$(RESET)          $(DESC_COLOR)Run all tests$(RESET)\n"
	@printf "  $(CMD_COLOR)format$(RESET)        $(DESC_COLOR)Format code with black and isort$(RESET)\n"
	@printf "  $(CMD_COLOR)lint$(RESET)          $(DESC_COLOR)Run linting with flake8$(RESET)\n"
	@printf "  $(CMD_COLOR)type-check$(RESET)    $(DESC_COLOR)Run type checking with mypy$(RESET)\n"
	@printf "  $(CMD_COLOR)check$(RESET)         $(DESC_COLOR)Run all quality checks$(RESET)\n"
	@printf "  $(CMD_COLOR)clean$(RESET)         $(DESC_COLOR)Clean up temporary files and caches$(RESET)\n\n"
	@printf "$(TITLE_COLOR)Quick Start:$(RESET)\n"
	@printf "  $(DESC_COLOR)1. make install$(RESET)\n"
	@printf "  $(DESC_COLOR)2. Configure tools/meta.yaml with your OCI compartments$(RESET)\n"
	@printf "  $(DESC_COLOR)3. make oke-version-report PROJECT=my-project STAGE=dev$(RESET)\n"
	@printf "  $(DESC_COLOR)4. make oke-upgrade REPORT=reports/oke_versions_my-project_dev.html$(RESET)\n"

# Installation and setup
install:
	@echo "📦 Installing dependencies..."
	cd tools && poetry install

dev-setup: install
	@echo "🛠️  Setting up development environment..."
	cd tools && poetry run pre-commit install
	@echo "✅ Development environment ready!"

# SSH Sync commands
ssh-sync:
	@echo "🔧 Running OCI SSH Sync (Generate SSH config)..."
	@echo "Usage: make ssh-sync PROJECT=<project_name> STAGE=<stage>"
	@echo "Example: make ssh-sync PROJECT=my-project STAGE=dev"
	@echo ""
	@if [ -z "$(PROJECT)" ] || [ -z "$(STAGE)" ]; then \
		echo "❌ Error: PROJECT and STAGE parameters are required"; \
		echo ""; \
		echo "Available projects and stages are defined in meta.yaml"; \
		echo "See meta.yaml.example for configuration format"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make ssh-sync PROJECT=my-project STAGE=dev"; \
		echo "  make ssh-sync PROJECT=my-project STAGE=staging"; \
		echo "  make ssh-sync PROJECT=my-project STAGE=prod"; \
		exit 1; \
	fi
	cd tools && poetry run python src/ssh_sync.py $(PROJECT) $(STAGE)

oke-version-report:
	@echo "📄 Generating OKE version HTML report..."
	@if [ -z "$(PROJECT)" ] || [ -z "$(STAGE)" ]; then \
		echo "❌ Error: PROJECT and STAGE parameters are required"; \
		echo "Usage: make oke-version-report PROJECT=<project_name> STAGE=<stage> [META=tools/meta.yaml] [OUTPUT_DIR=reports]"; \
		exit 1; \
	fi
	@META_FLAG=""; \
	if [ -n "$(META)" ]; then \
		case "$(META)" in \
			/*) META_FLAG="--config-file $(META)";; \
			*) META_FLAG="--config-file ../$(META)";; \
		esac; \
	fi; \
	OUTPUT_FLAG=""; \
	if [ -n "$(OUTPUT_DIR)" ]; then \
		case "$(OUTPUT_DIR)" in \
			/*) OUTPUT_FLAG="--output-dir $(OUTPUT_DIR)";; \
			*) OUTPUT_FLAG="--output-dir ../$(OUTPUT_DIR)";; \
		esac; \
	fi; \
	cd tools && poetry run python src/oke_version_report.py $(PROJECT) $(STAGE) $$META_FLAG $$OUTPUT_FLAG

oke-upgrade:
	@echo "🚀 Triggering OKE cluster upgrades..."
	@if [ -z "$(REPORT)" ]; then \
		echo "❌ Error: REPORT=<path_to_report.html> is required"; \
		echo "Usage: make oke-upgrade REPORT=reports/oke_versions_project_stage.html [TARGET_VERSION=1.34.1] [PROJECT=<name>] [STAGE=<env>] [REGION_FILTER=<id>] [CLUSTER=<ocid_or_name>] [DRY_RUN=true] [VERBOSE=true]"; \
		exit 1; \
	fi
	@REPORT_ARG=""; \
	case "$(REPORT)" in \
		/*) REPORT_ARG="$(REPORT)";; \
		*) REPORT_ARG="../$(REPORT)";; \
	esac; \
	TARGET_FLAG=""; \
	if [ -n "$(TARGET_VERSION)" ]; then \
		TARGET_FLAG="--target-version $(TARGET_VERSION)"; \
	fi; \
	PROJECT_FLAG=""; \
	if [ -n "$(PROJECT)" ]; then \
		PROJECT_FLAG="--project $(PROJECT)"; \
	fi; \
	STAGE_FLAG=""; \
	if [ -n "$(STAGE)" ]; then \
		STAGE_FLAG="--stage $(STAGE)"; \
	fi; \
	REGION_FLAG=""; \
	if [ -n "$(REGION_FILTER)" ]; then \
		REGION_FLAG="--region $(REGION_FILTER)"; \
	elif [ -z "$(REGION_FILTER)" ] && [ -z "$(REPORT)" ] && [ -n "$(REGION)" ]; then \
		REGION_FLAG="--region $(REGION)"; \
	fi; \
	CLUSTER_FLAG=""; \
	if [ -n "$(CLUSTER)" ]; then \
		CLUSTER_FLAG="--cluster $(CLUSTER)"; \
	fi; \
	DRY_RUN_FLAG=""; \
	if [ "$(DRY_RUN)" = "1" ] || [ "$(DRY_RUN)" = "true" ] || [ "$(DRY_RUN)" = "TRUE" ] || [ "$(DRY_RUN)" = "yes" ] || [ "$(DRY_RUN)" = "YES" ]; then \
		DRY_RUN_FLAG="--dry-run"; \
	fi; \
	VERBOSE_FLAG=""; \
	if [ "$(VERBOSE)" = "1" ] || [ "$(VERBOSE)" = "true" ] || [ "$(VERBOSE)" = "TRUE" ] || [ "$(VERBOSE)" = "yes" ] || [ "$(VERBOSE)" = "YES" ]; then \
		VERBOSE_FLAG="--verbose"; \
	fi; \
	cd tools && poetry run python src/oke_upgrade.py $$REPORT_ARG $$TARGET_FLAG $$PROJECT_FLAG $$STAGE_FLAG $$REGION_FLAG $$CLUSTER_FLAG $$DRY_RUN_FLAG $$VERBOSE_FLAG

oke-upgrade-node-pools:
	@echo "🌊 Triggering OKE node pool upgrades..."
	@if [ -z "$(REPORT)" ]; then \
		echo "❌ Error: REPORT=<path_to_report.html> is required"; \
		echo "Usage: make oke-upgrade-node-pools REPORT=reports/oke_versions_project_stage.html [TARGET_VERSION=1.34.1] [PROJECT=<name>] [STAGE=<env>] [REGION_FILTER=<id>] [CLUSTER=<ocid_or_name>] [NODE_POOL=<id_or_name>] [DRY_RUN=true] [VERBOSE=true]"; \
		exit 1; \
	fi
	@REPORT_ARG=""; \
	case "$(REPORT)" in \
		/*) REPORT_ARG="$(REPORT)";; \
		*) REPORT_ARG="../$(REPORT)";; \
	esac; \
	TARGET_FLAG=""; \
	if [ -n "$(TARGET_VERSION)" ]; then \
		TARGET_FLAG="--target-version $(TARGET_VERSION)"; \
	fi; \
	PROJECT_FLAG=""; \
	if [ -n "$(PROJECT)" ]; then \
		PROJECT_FLAG="--project $(PROJECT)"; \
	fi; \
	STAGE_FLAG=""; \
	if [ -n "$(STAGE)" ]; then \
		STAGE_FLAG="--stage $(STAGE)"; \
	fi; \
	REGION_FLAG=""; \
	if [ -n "$(REGION_FILTER)" ]; then \
		REGION_FLAG="--region $(REGION_FILTER)"; \
	elif [ -z "$(REGION_FILTER)" ] && [ -z "$(REPORT)" ] && [ -n "$(REGION)" ]; then \
		REGION_FLAG="--region $(REGION)"; \
	fi; \
	CLUSTER_FLAG=""; \
	if [ -n "$(CLUSTER)" ]; then \
		CLUSTER_FLAG="--cluster $(CLUSTER)"; \
	fi; \
	NODE_POOL_FLAG=""; \
	if [ -n "$(NODE_POOL)" ]; then \
		for NP in $(NODE_POOL); do \
			NODE_POOL_FLAG="$$NODE_POOL_FLAG --node-pool $$NP"; \
		done; \
	fi; \
	DRY_RUN_FLAG=""; \
	if [ "$(DRY_RUN)" = "1" ] || [ "$(DRY_RUN)" = "true" ] || [ "$(DRY_RUN)" = "TRUE" ] || [ "$(DRY_RUN)" = "yes" ] || [ "$(DRY_RUN)" = "YES" ]; then \
		DRY_RUN_FLAG="--dry-run"; \
	fi; \
	VERBOSE_FLAG=""; \
	if [ "$(VERBOSE)" = "1" ] || [ "$(VERBOSE)" = "true" ] || [ "$(VERBOSE)" = "TRUE" ] || [ "$(VERBOSE)" = "yes" ] || [ "$(VERBOSE)" = "YES" ]; then \
		VERBOSE_FLAG="--verbose"; \
	fi; \
	cd tools && poetry run python src/oke_node_pool_upgrade.py $$REPORT_ARG $$TARGET_FLAG $$PROJECT_FLAG $$STAGE_FLAG $$REGION_FLAG $$CLUSTER_FLAG $$NODE_POOL_FLAG $$DRY_RUN_FLAG $$VERBOSE_FLAG

ssh-help:
	@echo "🔧 SSH Sync Configuration Help"
	@echo ""
	@echo "Configuration:"
	@echo "  SSH Sync uses YAML configuration from meta.yaml file"
	@echo "  • Define your projects in meta.yaml (see meta.yaml.example)"
	@echo "  • Supports multiple stages: dev, staging, prod"
	@echo "  • Automatically creates session tokens for each region"
	@echo ""
	@echo "What SSH Sync does:"
	@echo "  1. Parses meta.yaml to get region:compartment_id pairs for project/stage"
	@echo "  2. Creates session tokens for each region"
	@echo "  3. Discovers OKE cluster worker nodes and ODO instances across all regions"
	@echo "  4. Finds appropriate bastions for each instance"
	@echo "  5. Generates SSH config entries with ProxyCommand for bastion access"
	@echo "  6. Writes SSH configuration to ssh_configs/<project>_<stage>.txt"
	@echo ""
	@echo "Usage:"
	@echo "  make ssh-sync PROJECT=<project> STAGE=<stage>"
	@echo ""
	@echo "Prerequisites:"
	@echo "  • OCI CLI installed: pip install oci-cli"
	@echo "  • Valid Oracle Cloud tenancy access"
	@echo "  • At least one existing OCI profile (DEFAULT) for session token creation"
	@echo "  • ossh command available for ProxyCommand (Oracle internal tool)"
	@echo ""
	@echo "Authentication Setup:"
	@echo "  oci session authenticate --profile-name DEFAULT --region us-phoenix-1"
	@echo ""
	@echo "Examples:"
	@echo "  make ssh-sync PROJECT=my-project STAGE=dev"
	@echo "  make ssh-sync PROJECT=my-project STAGE=staging"
	@echo "  make ssh-sync PROJECT=my-project STAGE=prod"
	@echo ""
	@echo "Output:"
	@echo "  SSH config file: ssh_configs/<project>_<stage>.txt"

# New command: check for newer images per instance
image-updates:
	@echo "🔎 Checking for newer images for compute instances..."
	@echo "Usage: make image-updates PROJECT=<project_name> STAGE=<stage>"
	@echo "Example: make image-updates PROJECT=my-project STAGE=dev"
	@echo ""
	@if [ -z "$(PROJECT)" ] || [ -z "$(STAGE)" ]; then \
		echo "❌ Error: PROJECT and STAGE parameters are required"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make image-updates PROJECT=my-project STAGE=dev"; \
		echo "  make image-updates PROJECT=my-project STAGE=staging"; \
		exit 1; \
	fi
	cd tools && poetry run python src/check_image_updates.py $(PROJECT) $(STAGE)


# OKE node pool image bump
oke-node-pool-bump:
	@CSV_INPUT="$(CSV)"; \
	if [ -z "$$CSV_INPUT" ]; then \
		CSV_INPUT="oci_image_updates_report.csv"; \
	fi; \
	case "$$CSV_INPUT" in \
		/*) CSV_ARG="$$CSV_INPUT";; \
		*) CSV_ARG="../$$CSV_INPUT";; \
	esac; \
	printf "⬆️  Bumping OKE node pool images from %s\n" "$$CSV_INPUT"; \
	DRY_RUN_FLAG=""; \
	if [ "$(DRY_RUN)" = "1" ] || [ "$(DRY_RUN)" = "true" ] || [ "$(DRY_RUN)" = "TRUE" ] || [ "$(DRY_RUN)" = "yes" ] || [ "$(DRY_RUN)" = "YES" ]; then \
		DRY_RUN_FLAG="--dry-run"; \
	fi; \
	CONFIG_FLAG=""; \
	if [ -n "$(CONFIG)" ]; then \
		CONFIG_FLAG="--config-file ../$(CONFIG)"; \
	fi; \
	POLL_FLAG=""; \
	if [ -n "$(POLL_SECONDS)" ]; then \
		POLL_FLAG="--poll-seconds $(POLL_SECONDS)"; \
	fi; \
	META_FLAG=""; \
	if [ -n "$(META)" ]; then \
		META_FLAG="--meta-file ../$(META)"; \
	fi; \
	VERBOSE_FLAG=""; \
	if [ "$(VERBOSE)" = "1" ] || [ "$(VERBOSE)" = "true" ] || [ "$(VERBOSE)" = "TRUE" ] || [ "$(VERBOSE)" = "yes" ] || [ "$(VERBOSE)" = "YES" ]; then \
		VERBOSE_FLAG="--verbose"; \
	fi; \
	cd tools && poetry run python src/node_cycle_pools.py --csv-path "$$CSV_ARG" $$POLL_FLAG $$CONFIG_FLAG $$META_FLAG $$DRY_RUN_FLAG $$VERBOSE_FLAG

# OKE node cycling (replace boot volumes)
oke-node-cycle:
	@if [ -z "$(REPORT)" ]; then \
		echo "❌ Error: REPORT=<file> is required"; \
		echo "Usage: make oke-node-cycle REPORT=reports/oke_versions_project_stage.html [GRACE_PERIOD=PT30M] [FORCE_AFTER_GRACE=true] [DRY_RUN=true] [VERBOSE=true]"; \
		exit 1; \
	fi
	@echo "🔁 Cycling OKE node pools from $(REPORT)"
	@REPORT_ARG=""; \
	case "$(REPORT)" in \
		/*) REPORT_ARG="$(REPORT)";; \
		*) REPORT_ARG="../$(REPORT)";; \
	esac; \
	GRACE_FLAG=""; \
	if [ -n "$(GRACE_PERIOD)" ]; then \
		GRACE_FLAG="--grace-period $(GRACE_PERIOD)"; \
	fi; \
	FORCE_FLAG=""; \
	if [ "$(FORCE_AFTER_GRACE)" = "1" ] || [ "$(FORCE_AFTER_GRACE)" = "true" ] || [ "$(FORCE_AFTER_GRACE)" = "TRUE" ] || [ "$(FORCE_AFTER_GRACE)" = "yes" ] || [ "$(FORCE_AFTER_GRACE)" = "YES" ]; then \
		FORCE_FLAG="--force-after-grace"; \
	fi; \
	DRY_RUN_FLAG=""; \
	if [ "$(DRY_RUN)" = "1" ] || [ "$(DRY_RUN)" = "true" ] || [ "$(DRY_RUN)" = "TRUE" ] || [ "$(DRY_RUN)" = "yes" ] || [ "$(DRY_RUN)" = "YES" ]; then \
		DRY_RUN_FLAG="--dry-run"; \
	fi; \
	VERBOSE_FLAG=""; \
	if [ "$(VERBOSE)" = "1" ] || [ "$(VERBOSE)" = "true" ] || [ "$(VERBOSE)" = "TRUE" ] || [ "$(VERBOSE)" = "yes" ] || [ "$(VERBOSE)" = "YES" ]; then \
		VERBOSE_FLAG="--verbose"; \
	fi; \
	cd tools && poetry run python src/oke_node_cycle.py "$$REPORT_ARG" $$GRACE_FLAG $$FORCE_FLAG $$DRY_RUN_FLAG $$VERBOSE_FLAG

delete-bucket:
	@if [ -z "$(PROJECT)" ] || [ -z "$(STAGE)" ] || [ -z "$(REGION)" ] || [ -z "$(BUCKET)" ]; then \
		echo "❌ Error: PROJECT, STAGE, REGION, and BUCKET parameters are required"; \
		echo "Usage: make delete-bucket PROJECT=<project> STAGE=<stage> REGION=<region> BUCKET=<bucket> [NAMESPACE=<namespace>]"; \
		exit 1; \
	fi
	@echo "🗑️  Deleting bucket '$(BUCKET)' from namespace $${NAMESPACE:-<tenancy default>}..."
	cd tools && poetry run python src/delete_resources.py \
		--project "$(PROJECT)" \
		--stage "$(STAGE)" \
		--region "$(REGION)" \
		bucket \
		--bucket-name "$(BUCKET)" \
		$$( [ -n "$(NAMESPACE)" ] && printf -- "--namespace %s" "$(NAMESPACE)" )

delete-oke-cluster:
	@if [ -z "$(PROJECT)" ] || [ -z "$(STAGE)" ] || [ -z "$(REGION)" ] || [ -z "$(CLUSTER_ID)" ]; then \
		echo "❌ Error: PROJECT, STAGE, REGION, and CLUSTER_ID parameters are required"; \
		echo "Usage: make delete-oke-cluster PROJECT=<project> STAGE=<stage> REGION=<region> CLUSTER_ID=<ocid> [SKIP_NODE_POOLS=true]"; \
		exit 1; \
	fi
	@echo "🗑️  Deleting OKE cluster '$(CLUSTER_ID)'..."
	cd tools && poetry run python src/delete_resources.py \
		--project "$(PROJECT)" \
		--stage "$(STAGE)" \
		--region "$(REGION)" \
		oke-cluster \
		--cluster-id "$(CLUSTER_ID)" \
		$$( [ "$(SKIP_NODE_POOLS)" = "1" ] || [ "$(SKIP_NODE_POOLS)" = "true" ] || [ "$(SKIP_NODE_POOLS)" = "TRUE" ] || [ "$(SKIP_NODE_POOLS)" = "yes" ] || [ "$(SKIP_NODE_POOLS)" = "YES" ] && printf -- "--skip-node-pools" )

# Testing
test:
	@echo "🧪 Running tests..."
	cd tools && poetry run pytest

test-verbose:
	@echo "🧪 Running tests with verbose output..."
	cd tools && poetry run pytest -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	cd tools && poetry run pytest --cov=src/oci_client --cov-report=term-missing

# Code quality
format:
	@echo "🎨 Formatting code..."
	cd tools && poetry run black src/ tests/
	cd tools && poetry run isort src/ tests/

lint:
	@echo "🔍 Running linting..."
	cd tools && poetry run flake8 src/ tests/

type-check:
	@echo "🔬 Running type checking..."
	cd tools && poetry run mypy src/

# Development workflow
check: format lint type-check test
	@echo "✅ All checks passed!"

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*~" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# Example environment setup (for documentation)
setup-example:
	@echo "📋 Example environment setup:"
	@echo ""
	@echo "# Copy and paste these commands, replacing with your actual values:"
	@echo "export OCI_COMPARTMENT_ID=ocid1.compartment.oc1..aaaaaaaaxxxxxxxyyyyyyy"
	@echo "export OCI_REGION=us-phoenix-1"
	@echo "export OCI_PROFILE=DEFAULT"
	@echo ""
	@echo "# Then run the SSH sync:"
	@echo "make ssh-sync PROJECT=my-project STAGE=dev"

# Quick start for new users
quickstart:
	@echo "🚀 Quick Start Guide"
	@echo ""
	@echo "1. Install dependencies:"
	@echo "   make install"
	@echo ""
	@echo "2. Set up your OCI authentication:"
	@echo "   oci session authenticate --profile-name DEFAULT --region us-phoenix-1"
	@echo ""
	@echo "3. Configure your projects:"
	@echo "   cp tools/meta.yaml.example tools/meta.yaml"
	@echo "   # Edit meta.yaml with your project names and compartment IDs"
	@echo ""
	@echo "4. Run SSH sync or OKE version report:"
	@echo "   make ssh-sync PROJECT=my-project STAGE=dev"
	@echo "   make oke-version-report PROJECT=my-project STAGE=dev"
	@echo ""
	@echo "For more help: make ssh-help"
