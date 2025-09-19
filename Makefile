start-prod:
	@MODE=prod docker compose up -d

start-dev:
	@MODE=dev docker compose up -d --build

start-dev-tunnel:
	ssh -N -L 18080:127.0.0.1:80 janus@192.168.1.7


manifest-mixtral:
	docker compose exec llm-brain ollama pull mixtral

manifest-mistral:
	docker compose exec llm-brain ollama pull mistral

down:
	docker compose down --volumes --remove-orphans

nuke-prod:
	docker compose --profile prod down --volumes --remove-orphans
	docker network prune -f

nuke-dev:
	docker compose --profile dev down --volumes --remove-orphans
	docker network prune -f

# utils
docker-status:
	docker-compose ps

dev-logs:
	@docker compose logs -f --tail=200

log-voice:
	docker compose logs -f voice-app

log-caddy:
	docker compose logs -f caddy

log-brain:
	docker compose logs -f llm-brain

log-tts:
	docker compose logs -f coqui

log-redis:
	docker compose logs -f redis

chat-logs:
	docker compose logs -f subscriber
