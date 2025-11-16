# AI Voice Assistant System

A self-hosted **voice AI assistant**. It runs as a small fleet of Docker containers on a single NVIDIA-GPU machine. For local/dev on a headless server, you’ll usually reach it via an **SSH port-forward** to Caddy on port 80; for production you’ll use **Caddy + Let’s Encrypt** on your public domain.

For background/motivation, see: <https://github.com/junebug-junie/Orion-Sapienform>

---

## Core Architecture

**Services (Docker Compose):**

- **voice-app** — FastAPI app (UI + WebSocket audio). Uses **Faster-Whisper** on GPU for STT.
- **llm-brain** — **Ollama** server for the LLM (Mistral/Mixtral/etc.). Uses GPU for inference.
- **coqui-tts** — **Coqui TTS** service for high-quality speech synthesis.
- **caddy** — **Caddy** reverse proxy for dev/prod routing and HTTPS in production.

---

## Features

- Push-to-talk **real-time voice** interaction  
- **Local AI** (STT + LLM on your hardware) for privacy & speed  
- **Natural TTS** via Coqui  
- **Dynamic UI**: Orion state visualizer + speech visualizer  
- **Settings**: persona (system prompt), temperature, context length, speech rate  
- **Conversation controls**: copy transcript, clear history  
- **Interruptible speech** (stop mid-utterance)

---

## Prerequisites

- Linux host with an **NVIDIA GPU** (driver installed)
- **Docker** + **Docker Compose v2**
- **NVIDIA Container Toolkit** (GPU passthrough to containers)
- **Dev (headless)**: SSH access from your laptop to the server
- **Prod**: public domain, DNS A record to your server’s public IP, router/NAT forwards for **80/443**, firewall open for **80/443**

---

## Project Layout

```
caddy/
  Caddyfile.dev
  Caddyfile.prod
docker-compose.yml
Dockerfile
Makefile
README.md
requirements.txt
scripts/
static/
templates/
```

---

## First-Time Setup

1. **Clone/place files** on the server.
2. **Caddy configs** (in repo):
   - `caddy/Caddyfile.dev` — plain HTTP on :80 (perfect for SSH port-forward)
     ```caddy
     :80 {
         reverse_proxy http://voice-app:8080
     }
     ```
   - `caddy/Caddyfile.prod` — public domain w/ auto-HTTPS
     ```caddy
     assistant.yourdomain.net {
         reverse_proxy http://voice-app:8080
     }
     ```
   The `docker-compose.yml` mounts `./caddy/Caddyfile.${MODE:-dev}` to `/etc/caddy/Caddyfile`.
3. **Build images (first time)**  
   ```bash
   docker compose build
   ```

---

## Runbooks

### A) Development (headless server, SSH tunnel to Caddy on :80)

**Start dev (attached logs):**
```bash
MODE=dev docker compose up --build
# Ctrl+C stops the stack
```

**From your laptop**, create a tunnel to the server:
```bash
ssh -N -L 18080:127.0.0.1:80 user@<server-lan-ip>
```

Open: **http://localhost:18080**

**Pull an LLM model (first time per volume):**
```bash
docker compose exec llm-brain ollama pull mistral
# or: docker compose exec llm-brain ollama pull mixtral
```

**Logs (compose-native):**
```bash
docker compose logs -f voice-app caddy llm-brain coqui-tts redis subscriber
# or per service:
docker compose logs -f voice-app
```

**Stop dev:**
```bash
docker compose down --remove-orphans
```

---

### B) Production (public domain with auto-HTTPS)

**Requirements**
- DNS A record: `assistant.yourdomain.net` → your server’s public IP
- Ports **80/443** reachable (router/NAT + firewall)
- Ensure nothing else (e.g., Tailscale Funnel/Serve) is binding 80/443

**Start prod (detached):**
```bash
MODE=prod docker compose up -d --build
```

Open: **https://assistant.yourdomain.net**

**Pull an LLM model (first time per volume):**
```bash
docker compose exec llm-brain ollama pull mistral
```

**Stop prod:**
```bash
docker compose down --remove-orphans
```

---

## Makefile (handy targets)

Add these to `Makefile` if you want one-liners:

```makefile
# Dev attached (pretty consolidated logs)
start-dev:
	@MODE=dev docker compose up --build

# Dev detached, then follow logs
start-dev-follow:
	@MODE=dev docker compose up -d --build
	@docker compose logs -f --tail=200

# Prod detached
start-prod:
	@MODE=prod docker compose up -d --build

# Generic logs (all services)
LOG_TAIL ?= 200
logs:
	@docker compose logs -f --tail=$(LOG_TAIL)

# Per-service logs: make log SVC=voice-app
SVC ?= voice-app
log:
	@docker compose logs -f --tail=$(LOG_TAIL) $(SVC)

# Stop / Nuke
stop:
	@docker compose down --remove-orphans

nuke:
	@docker compose down --volumes --remove-orphans || true
	@docker network prune -f || true
```

---

## LLM Notes & Performance (Ollama)

- **List models**:
  ```bash
  docker compose exec llm-brain ollama list
  ```
- **Pull a model**:
  ```bash
  docker compose exec llm-brain ollama pull mistral
  ```
- **Tune (optional, via Modelfile)** — e.g., reduce VRAM & latency:
  ```Dockerfile
  FROM mistral
  PARAMETER quantization q4_K_M
  PARAMETER gpu_layers 20
  PARAMETER num_batch 64
  ```
  Then inside the container:
  ```bash
  docker compose exec llm-brain ollama create mistral-tuned -f /root/.ollama/models/Modelfile
  ```

---

## Troubleshooting

**Caddyfile parse error**
```
Error: Unexpected next token after '{'
```
Cause: env-expanded multiline blocks.  
Fix: use separate files `caddy/Caddyfile.dev` and `caddy/Caddyfile.prod` as above.

**Ports busy (80/443)**
```
failed to bind host port ... address already in use
```
Check:
```bash
sudo lsof -i :80 -P -n
sudo lsof -i :443 -P -n
```
Disable Tailscale Serve/Funnel if running:
```bash
sudo tailscale serve reset || true
sudo tailscale funnel --https=443 off || true
sudo tailscale funnel --https=8443 off || true
```
Restart Caddy:
```bash
docker compose restart caddy
```

**Let’s Encrypt rate limits (HTTP 429)**  
Wait for cooldown (see Caddy logs). To test safely, keep using **dev** first; for alt CAs/staging, create a separate prod Caddyfile variant.

**Bind-mount error (file vs directory)**
```
Are you trying to mount a directory onto a file?
```
Ensure `caddy/Caddyfile.dev` & `.prod` exist as **files**. Use long bind syntax in compose.

**App is healthy in container but not on host**  
Remember the host port for `voice-app` might be random unless pinned. In dev we route through Caddy on port 80; otherwise:
```bash
docker compose port voice-app 8080  # shows host mapping
```

**Quick health check from inside container**
```bash
docker compose exec voice-app curl -sSf http://localhost:8080/docs | head -n 10
```

---

## Security

- Dev uses **plain HTTP** internally and an **SSH tunnel** from your laptop — simple and private.
- Prod uses **Caddy auto-HTTPS** with trusted certificates.
- If you prefer a private mesh in dev, you can use **Tailscale Serve** instead of SSH port-forwarding (disabled by default to avoid port conflicts).

---

## License

This repository includes third-party components (Coqui TTS, Ollama model weights, etc.) with their own licenses. Review those licenses before commercial use.
