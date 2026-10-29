.PHONY: help verify score test submission clean lint format

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

verify: ## Verify baseline circuits (requires Linux with kickmix.so)
	@echo "Verifying baseline circuits..."
	@python -m tools.verify bench1 bench1/baseline/invsqrt.kmb --dry-run
	@python -m tools.verify bench2 bench2/baseline/dqi.kmb --dry-run
	@python -m tools.verify bench3 bench3/baseline/dfthcsos --dry-run

score: ## Calculate current competition score from best/ artifacts
	@echo "Calculating competition score..."
	@python -m tools.score

test: ## Run all unit tests
	@echo "Running unit tests..."
	@python -m pytest tests/ -v

submission: ## Build submission.zip from bench*/best/ artifacts
	@echo "Building submission.zip..."
	@python -m tools.build_submission

clean: ## Remove temporary files and caches
	@echo "Cleaning temporary files..."
	@rm -rf .pytest_cache __pycache__ .ruff_cache .mypy_cache
	@rm -rf bench*/candidates/*
	@touch bench*/candidates/.gitkeep

lint: ## Run ruff linter
	@echo "Running linter..."
	@ruff check tools/ tests/

format: ## Format code with black
	@echo "Formatting code..."
	@black tools/ tests/

setup: ## Install development dependencies
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
