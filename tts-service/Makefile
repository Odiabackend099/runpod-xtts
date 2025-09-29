# CallWaiting.ai TTS Service Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev test test-unit test-integration lint format clean build run docker-build docker-run docker-stop deploy optimize gpu-setup load-test

# Default target
help:
	@echo "CallWaiting.ai TTS Service - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     Install dependencies"
	@echo "  dev         Start development server"
	@echo "  run         Run production server"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run all tests"
	@echo "  test-unit   Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-coverage  Run tests with coverage report"
	@echo "  load-test   Run load tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint        Run linting checks"
	@echo "  format      Format code with black"
	@echo "  clean       Clean temporary files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run with Docker Compose"
	@echo "  docker-stop   Stop Docker containers"
	@echo ""
	@echo "Performance:"
	@echo "  optimize    Run performance optimization"
	@echo "  gpu-setup   Setup GPU support"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy      Deploy to production"
	@echo "  health      Check service health"

# Development
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

dev:
	@echo "🚀 Starting development server..."
	python -m src.server --reload

run:
	@echo "🚀 Starting production server..."
	python -m src.server

# Testing
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

load-test:
	@echo "📊 Running load tests..."
	python scripts/load_test.py --test-type concurrent --concurrent 10 --duration 60

# Code Quality
lint:
	@echo "🔍 Running linting checks..."
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	mypy src/ --ignore-missing-imports

format:
	@echo "🎨 Formatting code..."
	black src/ tests/ --line-length=100
	isort src/ tests/ --profile=black

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/

# Docker
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t tts-service .

docker-run:
	@echo "🐳 Starting services with Docker Compose..."
	docker-compose up --build

docker-stop:
	@echo "🐳 Stopping Docker containers..."
	docker-compose down

# Performance
optimize:
	@echo "⚡ Running performance optimization..."
	python scripts/optimize_performance.py --save

gpu-setup:
	@echo "🎮 Setting up GPU support..."
	python scripts/gpu_setup.py

# Deployment
deploy:
	@echo "🚀 Deploying to production..."
	@echo "This would deploy to your configured environment"
	@echo "Update this target based on your deployment strategy"

health:
	@echo "🏥 Checking service health..."
	curl -f http://localhost:8000/v1/health || echo "❌ Service not healthy"

# Database
db-migrate:
	@echo "🗄️  Running database migrations..."
	alembic upgrade head

db-reset:
	@echo "🗄️  Resetting database..."
	alembic downgrade base
	alembic upgrade head

# Monitoring
logs:
	@echo "📋 Showing service logs..."
	docker-compose logs -f tts-service

metrics:
	@echo "📊 Showing service metrics..."
	curl -H "Authorization: Bearer sk_admin_1234567890abcdef" \
		http://localhost:8000/v1/metrics | jq

# Voice Management
voices:
	@echo "🎤 Listing available voices..."
	curl -H "Authorization: Bearer sk_test_1234567890abcdef" \
		http://localhost:8000/v1/voices | jq

upload-voice:
	@echo "🎤 Uploading test voice..."
	@echo "Usage: make upload-voice VOICE_ID=test_voice AUDIO_FILE=test.wav"
	@if [ -z "$(VOICE_ID)" ] || [ -z "$(AUDIO_FILE)" ]; then \
		echo "❌ Please provide VOICE_ID and AUDIO_FILE"; \
		exit 1; \
	fi
	curl -X POST \
		-H "Authorization: Bearer sk_test_1234567890abcdef" \
		-F "voice_id=$(VOICE_ID)" \
		-F "name=Test Voice" \
		-F "description=Test voice for development" \
		-F "language=en" \
		-F "audio_file=@$(AUDIO_FILE)" \
		http://localhost:8000/v1/voices/upload

# Testing with different scenarios
test-synthesis:
	@echo "🎤 Testing TTS synthesis..."
	curl -X POST \
		-H "Authorization: Bearer sk_test_1234567890abcdef" \
		-F "text=Hello from CallWaiting.ai TTS service" \
		-F "voice_id=naija_female" \
		-F "streaming=true" \
		--output test_output.wav \
		http://localhost:8000/v1/synthesize
	@echo "✅ Audio saved to test_output.wav"

test-ssml:
	@echo "🎤 Testing SSML synthesis..."
	curl -X POST \
		-H "Authorization: Bearer sk_test_1234567890abcdef" \
		-F "text=Hello world" \
		-F "ssml=<speak><break time='0.5s'/>Hello <emphasis level='strong'>world</emphasis></speak>" \
		-F "voice_id=naija_female" \
		--output test_ssml_output.wav \
		http://localhost:8000/v1/synthesize
	@echo "✅ SSML audio saved to test_ssml_output.wav"

# Development helpers
setup-dev:
	@echo "🛠️  Setting up development environment..."
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Development environment ready"
	@echo "💡 Activate with: source .venv/bin/activate"

install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	pip install black isort flake8 mypy pytest-cov

# Production helpers
build-prod:
	@echo "🏗️  Building production image..."
	docker build -f Dockerfile.prod -t tts-service:prod .

run-prod:
	@echo "🚀 Running production container..."
	docker run -d \
		--name tts-service-prod \
		-p 8000:8000 \
		-e HOST=0.0.0.0 \
		-e PORT=8000 \
		tts-service:prod

stop-prod:
	@echo "⏹️  Stopping production container..."
	docker stop tts-service-prod
	docker rm tts-service-prod

# Backup and restore
backup:
	@echo "💾 Creating backup..."
	tar -czf backup_$(shell date +%Y%m%d_%H%M%S).tar.gz \
		voice_storage/ \
		*.db \
		config/

restore:
	@echo "📥 Restoring from backup..."
	@echo "Usage: make restore BACKUP_FILE=backup_20240101_120000.tar.gz"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Please provide BACKUP_FILE"; \
		exit 1; \
	fi
	tar -xzf $(BACKUP_FILE)

# Security
security-scan:
	@echo "🔒 Running security scan..."
	safety check
	bandit -r src/

# Documentation
docs:
	@echo "📚 Generating documentation..."
	pdoc --html src/ --output-dir docs/
	@echo "✅ Documentation generated in docs/"

# Quick start
quick-start:
	@echo "🚀 Quick start setup..."
	make install
	make docker-run
	@echo "✅ Service should be running at http://localhost:8000"
	@echo "📚 API docs: http://localhost:8000/docs"
	@echo "🏥 Health check: http://localhost:8000/v1/health"
