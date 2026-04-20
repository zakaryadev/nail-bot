# ──────────────────────────────────────────────────────────
#  nail-bot — Docker management shortcuts
#  Usage: make <command>
# ──────────────────────────────────────────────────────────

.DEFAULT_GOAL := help
COMPOSE = docker compose
IMAGE   = nail_bot

.PHONY: help up down restart rebuild logs shell status clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Build (if needed) and start the bot in background
	@if [ ! -f .env ]; then \
		echo "❌  .env file not found. Run: cp .env.example .env"; \
		exit 1; \
	fi
	$(COMPOSE) up -d --build

down: ## Stop and remove containers
	$(COMPOSE) down

restart: ## Restart the bot container
	$(COMPOSE) restart bot

rebuild: ## Force full rebuild (no cache) and restart
	$(COMPOSE) down
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

logs: ## Tail live logs (Ctrl+C to exit)
	$(COMPOSE) logs -f bot

shell: ## Open a bash shell inside the running container
	$(COMPOSE) exec bot /bin/sh

status: ## Show container status and health
	$(COMPOSE) ps

clean: ## Remove containers, volumes, and dangling images
	$(COMPOSE) down -v
	docker image prune -f
