.PHONY: run install test clean docker-build docker-run venv

# Setup virtual environment
venv:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "Virtual environment created! Activate it with:"
	@echo "  source venv/bin/activate"

# Install dependencies (in current environment)
install:
	pip install -r requirements.txt

# Run server (auto-detects venv if active)
run:
	@if [ -d "venv" ] && [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Virtual environment exists but not activated."; \
		echo "Activate with: source venv/bin/activate"; \
		echo "Or running with venv python..."; \
		./venv/bin/uvicorn src.app:app --reload --host 0.0.0.0 --port 8000; \
	else \
		uvicorn src.app:app --reload --host 0.0.0.0 --port 8000; \
	fi

test:
	pytest -v

clean:
	rm -rf logs/*
	rm -rf runs/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t swebench-green-agent .

docker-run:
	docker run -p 8000:8000 swebench-green-agent

setup:
	mkdir -p logs runs data/tasks
