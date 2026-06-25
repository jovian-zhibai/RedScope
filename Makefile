.PHONY: setup dev build test clean

setup:
	@echo "=== Installing backend dependencies ==="
	cd backend && pip install -r requirements.txt
	@echo "=== Installing frontend dependencies ==="
	cd frontend && npm install
	@echo "=== Setup complete ==="

dev:
	@echo "Starting backend..."
	cd backend && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

test:
	cd backend && python -m pytest -v
	cd frontend && npm test

migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)"
	cd backend && alembic upgrade head

backup:
	bash scripts/backup.sh

restore:
	bash scripts/restore.sh $(file)

clean:
	docker compose down -v
	rm -rf backend/__pycache__ backend/**/__pycache__
	rm -rf frontend/node_modules frontend/dist
