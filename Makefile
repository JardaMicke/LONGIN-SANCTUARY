##############################################################
# LONGIN SANCTUARY — Makefile
# Usage: make <target>
##############################################################

.PHONY: help up down dev-api dev-frontend logs db-reset install test

help:
	@echo "LONGIN SANCTUARY — Available commands:"
	@echo "  make up           Start all Docker services (DB, Redis, Qdrant)"
	@echo "  make down         Stop all Docker services"
	@echo "  make dev-api      Run backend API in dev mode (hot reload)"
	@echo "  make dev-frontend Run Next.js frontend in dev mode"
	@echo "  make logs         Follow Docker service logs"
	@echo "  make db-reset     Reset database (WARNING: deletes all data)"
	@echo "  make install      Install all Python dependencies"
	@echo "  make test         Run backend tests"
	@echo "  make cluster-join Join this node to a cluster master"

# ── Docker services ─────────────────────────────────────────
up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "✅ Services started. PostgreSQL: 5432, Redis: 6379, Qdrant: 6333"

down:
	docker compose -f docker/docker-compose.yml down

logs:
	docker compose -f docker/docker-compose.yml logs -f

db-reset:
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml up -d postgres redis qdrant
	@echo "⚠️  Database reset complete."

# ── Development ─────────────────────────────────────────────
install:
	cd backend && pip install -r requirements.txt

dev-api:
	cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

dev-frontend:
	cd frontend && npm run dev

# ── Database migrations ─────────────────────────────────────
migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

# ── Testing ─────────────────────────────────────────────────
test:
	cd backend && pytest tests/ -v

# ── Cluster ─────────────────────────────────────────────────
cluster-join:
	@read -p "Master IP: " master_ip; \
	python scripts/cluster_agent.py --master $$master_ip
