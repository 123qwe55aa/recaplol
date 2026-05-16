.PHONY: help dev build up down logs ps test clean

help:
	@echo "Available commands:"
	@echo "  make dev      - Run locally with uvicorn (requires .env)"
	@echo "  make build    - Build Docker image"
	@echo "  make up       - Start all services with docker-compose"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make ps       - Show running containers"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove containers and volumes"

dev:
	python main.py

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

ps:
	docker-compose ps

test:
	python -m pytest -v

clean:
	docker-compose down -v --remove-orphans
