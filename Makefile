# Shortcuts. Local targets assume `micromamba activate pitwall`.
.PHONY: env api web test test-tasks test-network lint fmt mlflow up down docker-test

env:            ## create the micromamba env (Python + Node + PyTorch/MPS)
	micromamba create -f environment.yml -y

api:            ## FastAPI with auto-reload on :8000  (interactive docs at /docs)
	uvicorn pitwall.api.main:app --reload --port 8000 --app-dir backend/src

web:            ## React dev server on :5173 (proxies /api to :8000)
	cd frontend && npm install && npm run dev

test:           ## backend + frontend tests (offline)
	cd backend && pytest
	cd frontend && npm test

test-tasks:     ## acceptance tests for docs/tasks (fail until you implement them)
	cd backend && pytest -m task

test-network:   ## live checks against OpenF1 / Jolpica
	cd backend && pytest -m network

lint:
	cd backend && ruff check src tests scripts && ruff format --check src tests scripts
	cd frontend && npm run typecheck && npm run lint

fmt:
	cd backend && ruff format src tests scripts && ruff check --fix src tests scripts
	cd frontend && npm run format

mlflow:         ## experiment UI on :5000
	mlflow ui --backend-store-uri sqlite:///mlflow.db

up:             ## whole app in Docker on :8080
	docker compose up --build -d

down:
	docker compose down

docker-test:    ## backend lint + tests inside the container
	docker compose run --rm --build test
