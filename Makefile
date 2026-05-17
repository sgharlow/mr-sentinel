.PHONY: install test run-local docker-build docker-run lint clean

install:
	pip install -r requirements-dev.txt

test:
	pytest

run-local:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

docker-build:
	docker build -t mr-sentinel:dev .

docker-run:
	docker run --rm -p 8080:8080 --env-file .env.local mr-sentinel:dev

lint:
	ruff check app tests

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ app/__pycache__ tests/__pycache__
