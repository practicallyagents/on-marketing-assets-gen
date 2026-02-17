.PHONY: setup index run web test clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies and build product index
	uv sync
	uv run python scripts/build_product_index.py

index: ## Rebuild the product index from scraped data
	uv run python scripts/build_product_index.py

run: ## Run the agent pipeline in CLI mode
	uv run adk run agents

web: ## Start the ADK web UI (browser-based)
	uv run adk web .

test: ## Run tests
	uv run pytest tests/ -v

clean: ## Remove generated output files
	rm -rf output/*.png output/*.json
	@echo "Cleaned output directory"
