.PHONY: up down build migrate test certs seed

# Generate self-signed TLS cert for local dev
certs:
	mkdir -p nginx/certs
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	  -keyout nginx/certs/server.key \
	  -out nginx/certs/server.crt \
	  -subj "/C=TR/ST=Ankara/L=Ankara/O=CAERN/CN=localhost"

# Copy .env.example → .env if missing
.env:
	cp .env.example .env

# Build / rebuild all images without (re)starting
build:
	sudo docker compose build

# Start all services
up: .env certs
	sudo docker compose up -d --build

# Run DB migrations
migrate:
	sudo docker compose exec api alembic upgrade head

# Tear everything down (preserves volumes)
down:
	sudo docker compose down

# Full reset including volumes
reset:
	sudo docker compose down -v

# Backend tests
test:
	sudo docker compose exec api pytest

# Create initial admin user (run after migrate)
seed:
	sudo docker compose exec api python seed.py
