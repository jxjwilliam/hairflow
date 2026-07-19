# ===========================================================================
# HairFlow — AI Virtual Hairstyle Try-On
# ===========================================================================
# Usage:
#   make init        Install all dependencies
#   make start       Start backend + frontend
#   make stop        Stop all services
#   make restart     Stop + start
#   make check       Health check (ComfyUI, backend, frontend)
#   make status      Alias for check
#   make logs        Tail backend logs
#   make test        Run backend tests
#   make clean       Clean up caches and temp files
#   make thumbnails  Regenerate catalog thumbnails
# ===========================================================================

SHELL := /bin/bash
.PHONY: init start stop restart check status logs test clean thumbnails \
        discover-video-nodes backend frontend backend-stop frontend-stop help

# ── Config ────────────────────────────────────────────────────────────────
BACKEND_DIR  := backend
MOBILE_DIR   := mobile
BACKEND_PORT ?= 8000
COMFYUI_URL  ?= http://127.0.0.1:8188
PID_FILE     := /tmp/hairflow-backend.pid
LOG_FILE     := /tmp/hairflow-backend.log

# ── Colors ────────────────────────────────────────────────────────────────
BOLD := \033[1m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
CYAN := \033[36m
RESET := \033[0m

# ===========================================================================
# Init
# ===========================================================================

init: ## Install all dependencies (backend + frontend)
	@printf "$(BOLD)==> Installing backend dependencies...$(RESET)\n"
	cd $(BACKEND_DIR) && python3 -m venv .venv 2>/dev/null || true
	cd $(BACKEND_DIR) && .venv/bin/pip install -q -r requirements.txt
	@printf "$(GREEN)  ✔ Backend dependencies installed$(RESET)\n"
	@printf "$(BOLD)==> Installing frontend dependencies...$(RESET)\n"
	cd $(MOBILE_DIR) && npm install --silent
	@printf "$(GREEN)  ✔ Frontend dependencies installed$(RESET)\n"
	@printf "$(BOLD)==> Creating .env from .env.example (if not exists)...$(RESET)\n"
	@test -f $(BACKEND_DIR)/.env || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env
	@printf "$(GREEN)  ✔ Init complete. Run 'make start' to launch.$(RESET)\n"

# ===========================================================================
# Start
# ===========================================================================

backend: ## Start backend server only
	@printf "$(BOLD)==> Starting backend on 0.0.0.0:$(BACKEND_PORT)...$(RESET)\n"
	@mkdir -p $(BACKEND_DIR)/output
	cd $(BACKEND_DIR) && nohup uvicorn app.main:app \
		--reload \
		--host 0.0.0.0 \
		--port $(BACKEND_PORT) \
		> $(LOG_FILE) 2>&1 & \
		echo $$! > $(PID_FILE)
	@sleep 2
	@if kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		printf "$(GREEN)  ✔ Backend running on http://localhost:$(BACKEND_PORT)$(RESET)\n"; \
	else \
		printf "$(RED)  ✖ Backend failed to start. Check logs: tail -f $(LOG_FILE)$(RESET)\n"; \
	fi

frontend: ## Start frontend (Expo) only
	@printf "$(BOLD)==> Starting Expo frontend...$(RESET)\n"
	cd $(MOBILE_DIR) && npx expo start &

start: check-comfyui ## Start backend + frontend
	@$(MAKE) backend
	@$(MAKE) frontend
	@printf "\n$(BOLD)$(GREEN)━━━ HairFlow is running ━━━$(RESET)\n"
	@printf "  Backend : $(CYAN)http://localhost:$(BACKEND_PORT)$(RESET)\n"
	@printf "  Frontend: $(CYAN)http://localhost:8081$(RESET) (Expo dev tools)\n"
	@printf "  ComfyUI : $(CYAN)$(COMFYUI_URL)$(RESET)\n"
	@printf "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)\n"
	@printf "  %s\n" "Run 'make stop' to stop all services."
	@printf "  %s\n\n" "Run 'make logs' to tail backend logs."

# ===========================================================================
# Stop
# ===========================================================================

backend-stop: ## Stop backend server
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null && \
		printf "$(YELLOW)  ✔ Backend stopped$(RESET)\n" || \
		printf "$(YELLOW)  - Backend was not running$(RESET)\n"; \
		rm -f $(PID_FILE); \
	else \
		printf "$(YELLOW)  - No PID file found$(RESET)\n"; \
	fi

frontend-stop: ## Stop Expo frontend (by finding expo process)
	@pkill -f "expo start" 2>/dev/null && \
		printf "$(YELLOW)  ✔ Frontend stopped$(RESET)\n" || \
		printf "$(YELLOW)  - Frontend was not running$(RESET)\n"

stop: ## Stop all services
	@printf "$(BOLD)==> Stopping all services...$(RESET)\n"
	@$(MAKE) backend-stop
	@$(MAKE) frontend-stop
	@printf "$(YELLOW)  ✔ All services stopped$(RESET)\n"

restart: stop start ## Restart all services

# ===========================================================================
# Health check
# ===========================================================================

check-comfyui:
	@printf "$(BOLD)==> Checking ComfyUI...$(RESET)\n"
	@status=$$(curl -s -o /dev/null -w "%{http_code}" $(COMFYUI_URL)/system_stats 2>/dev/null || echo "000"); \
	if [ "$$status" = "200" ]; then \
		printf "$(GREEN)  ✔ ComfyUI is running at $(COMFYUI_URL)$(RESET)\n"; \
	else \
		printf "$(RED)  ✖ ComfyUI is NOT running at $(COMFYUI_URL)$(RESET)\n"; \
		printf "$(RED)    Start it with Pinokio or 'python main.py'$(RESET)\n"; \
		printf "$(RED)    See docs/ds_comfyui_setup.md for details.$(RESET)\n"; \
	fi

check-backend:
	@printf "$(BOLD)==> Checking backend...$(RESET)\n"
	@status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$(BACKEND_PORT)/ 2>/dev/null || echo "000"); \
	if [ "$$status" = "200" ]; then \
		printf "$(GREEN)  ✔ Backend is running at http://localhost:$(BACKEND_PORT)$(RESET)\n"; \
	else \
		printf "$(RED)  ✖ Backend is NOT running$(RESET)\n"; \
	fi

check-frontend:
	@printf "$(BOLD)==> Checking frontend...$(RESET)\n"
	@status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 2>/dev/null || echo "000"); \
	if [ "$$status" != "000" ]; then \
		printf "$(GREEN)  ✔ Frontend is running at http://localhost:8081$(RESET)\n"; \
	else \
		printf "$(RED)  ✖ Frontend is NOT running$(RESET)\n"; \
	fi

check: check-comfyui check-backend check-frontend ## Check status of all services
	@printf "\n$(BOLD)Quick URLs:$(RESET)\n"
	@printf "  API docs : $(CYAN)http://localhost:$(BACKEND_PORT)/docs$(RESET)\n"
	@printf "  Templates: $(CYAN)http://localhost:$(BACKEND_PORT)/api/templates$(RESET)\n"

status: check ## Alias for check

# ===========================================================================
# Logs
# ===========================================================================

logs: ## Tail backend logs
	@if [ -f $(LOG_FILE) ]; then \
		tail -f $(LOG_FILE); \
	else \
		printf "$(RED)No log file found. Start backend first.$(RESET)\n"; \
	fi

# ===========================================================================
# Test
# ===========================================================================

test: ## Run backend tests
	@printf "$(BOLD)==> Running backend tests...$(RESET)\n"
	cd $(BACKEND_DIR) && PYTHONPATH=. python -m pytest tests/ -v

# ===========================================================================
# Clean
# ===========================================================================

clean: ## Clean up caches, temp files, and output
	@printf "$(BOLD)==> Cleaning...$(RESET)\n"
	@rm -rf $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/app/__pycache__
	@rm -rf $(BACKEND_DIR)/app/**/__pycache__
	@rm -rf $(BACKEND_DIR)/.pytest_cache
	@rm -rf $(MOBILE_DIR)/.expo $(MOBILE_DIR)/node_modules/.cache
	@printf "$(GREEN)  ✔ Caches cleaned$(RESET)\n"

clean-all: clean ## Deep clean (remove venv + node_modules)
	@printf "$(BOLD)==> Deep cleaning...$(RESET)\n"
	@rm -rf $(BACKEND_DIR)/.venv
	@rm -rf $(MOBILE_DIR)/node_modules
	@rm -rf $(BACKEND_DIR)/output/*.png
	@printf "$(YELLOW)  ✔ Deep clean done. Run 'make init' to reinstall.$(RESET)\n"

# ===========================================================================
# Catalog thumbnails
# ===========================================================================

thumbnails: ## Regenerate catalog thumbnails via ComfyUI
	@printf "$(BOLD)==> Regenerating catalog thumbnails...$(RESET)\n"
	cd $(BACKEND_DIR) && python scripts/generate_thumbnails.py

thumbnails-force: ## Regenerate all thumbnails (overwrite existing)
	@printf "$(BOLD)==> Regenerating ALL thumbnails (force)...$(RESET)\n"
	cd $(BACKEND_DIR) && python scripts/generate_thumbnails.py --force

discover-video-nodes: ## Probe ComfyUI for LTX/Hunyuan/AnimateDiff nodes
	cd $(BACKEND_DIR) && \
	  COMFYUI_URL=$(COMFYUI_URL) $(or $(wildcard $(BACKEND_DIR)/.venv/bin/python),$(wildcard venv/bin/python),python3) \
	  scripts/discover_video_nodes.py

# ===========================================================================
# Database
# ===========================================================================

db-reset: ## Delete and recreate the database
	@printf "$(BOLD)==> Resetting database...$(RESET)\n"
	@rm -f $(BACKEND_DIR)/hairstyle.db
	@printf "$(YELLOW)  ✔ Database deleted. It will auto-recreate on next backend start.$(RESET)\n"

# ===========================================================================
# Help
# ===========================================================================

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(BOLD)%-22s$(RESET) %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
