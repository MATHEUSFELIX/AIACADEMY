# ============================================================
# MasterAI Academy — Makefile
# Comandos de desenvolvimento
# ============================================================

.PHONY: help setup up down logs shell-backend shell-db seed test lint

# Cores
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

help: ## Mostra este menu
	@echo ""
	@echo "  $(GREEN)MasterAI Academy — Comandos$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

setup: ## Primeira configuração — copia .env e instala dependências
	@echo "$(GREEN)Configurando ambiente...$(RESET)"
	@[ -f .env ] || cp .env.example .env && echo "  ✓ .env criado — preencha as variáveis"
	@[ -d frontend/node_modules ] || (cd frontend && npm install && echo "  ✓ Frontend deps instaladas")
	@[ -d backend/.venv ] || (cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && echo "  ✓ Backend deps instaladas")
	@echo "$(GREEN)Pronto! Rode: make up$(RESET)"

up: ## Sobe todos os serviços
	@echo "$(GREEN)Subindo serviços...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)Serviços rodando:$(RESET)"
	@echo "  Frontend  → http://localhost:3000"
	@echo "  Backend   → http://localhost:8000"
	@echo "  Docs API  → http://localhost:8000/docs"
	@echo "  ChromaDB  → http://localhost:8001"

up-infra: ## Sobe só a infraestrutura (Postgres + ChromaDB + Redis)
	docker compose up -d postgres chromadb redis
	@echo "$(GREEN)Infraestrutura pronta$(RESET)"

down: ## Para todos os serviços
	docker compose down

down-volumes: ## Para serviços E apaga volumes (reset completo)
	@echo "$(YELLOW)Atenção: isso apaga todos os dados locais$(RESET)"
	docker compose down -v

logs: ## Mostra logs de todos os serviços
	docker compose logs -f

logs-backend: ## Mostra logs do backend
	docker compose logs -f backend

logs-frontend: ## Mostra logs do frontend
	docker compose logs -f frontend

shell-backend: ## Abre shell no container do backend
	docker compose exec backend bash

shell-db: ## Abre psql no PostgreSQL
	docker compose exec postgres psql -U masterai -d masterai_academy

seed: ## Popula o banco com as aulas (conteúdo JSON)
	@echo "$(GREEN)Populando aulas no banco...$(RESET)"
	docker compose exec backend python -m scripts.seed_lessons
	@echo "$(GREEN)Seed concluído$(RESET)"

seed-reset: ## Apaga e repopula as aulas
	docker compose exec backend python -m scripts.seed_lessons --reset

test-backend: ## Roda testes do backend
	@echo "$(GREEN)Rodando testes backend...$(RESET)"
	docker compose exec backend pytest tests/ -v --tb=short

test-e2e: ## Roda testes E2E com Playwright
	@echo "$(GREEN)Rodando testes E2E...$(RESET)"
	cd frontend && npx playwright test

lint-backend: ## Lint do backend (ruff + mypy)
	docker compose exec backend ruff check .
	docker compose exec backend mypy .

lint-frontend: ## Lint do frontend (ESLint + TypeScript)
	cd frontend && npm run lint
	cd frontend && npm run type-check

lint: lint-backend lint-frontend ## Lint de tudo

migrate: ## Aplica migrations pendentes
	docker compose exec backend alembic upgrade head

migration: ## Cria nova migration (uso: make migration name=nome_da_migration)
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

health: ## Verifica saúde de todos os serviços
	@echo "$(GREEN)Verificando serviços...$(RESET)"
	@curl -sf http://localhost:8000/health && echo "  ✓ Backend OK" || echo "  ✗ Backend OFFLINE"
	@curl -sf http://localhost:8001/api/v1/heartbeat && echo "  ✓ ChromaDB OK" || echo "  ✗ ChromaDB OFFLINE"
	@docker compose exec redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d= -f2) ping 2>/dev/null | grep -q PONG && echo "  ✓ Redis OK" || echo "  ✗ Redis OFFLINE"
	@docker compose exec postgres pg_isready -U masterai 2>/dev/null && echo "  ✓ Postgres OK" || echo "  ✗ Postgres OFFLINE"

reset: down-volumes up ## Reset completo — apaga tudo e recomeça
	@sleep 5
	@make seed
	@echo "$(GREEN)Reset completo — ambiente limpo$(RESET)"
