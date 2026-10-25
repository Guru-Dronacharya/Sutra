.PHONY: up down test seed demo eval tamper-demo lint clean help

help:
	@echo "Sutra - AI Governance & Compliance Intelligence Platform"
	@echo "--------------------------------------------------------"
	@echo "make up          - Start all containers via Docker Compose"
	@echo "make down        - Stop all containers"
	@echo "make test        - Run cross-service automated test suites"
	@echo "make seed        - Seed database with FinSure Bank models & sample corpus"
	@echo "make demo        - Execute live proxy traffic demo"
	@echo "make eval        - Run full benchmark evaluation suites"
	@echo "make tamper-demo - Demonstrate cryptographic audit ledger tamper detection"

up:
	docker compose up --build -d

down:
	docker compose down

test:
	python -m pytest tests/ -v

seed:
	python scripts/seed.py

demo:
	python scripts/demo_client.py

eval:
	python eval/run_all.py

tamper-demo:
	python scripts/tamper_demo.py

lint:
	python -m ruff check . || true

clean:
	rm -rf __pycache__ .pytest_cache *.db ./data/chroma
