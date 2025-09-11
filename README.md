Orion AI Voice System

This service is a production-grade, self-hosted voice AI assistant. It leverages a multi-container Docker architecture to create a scalable, high-performance system that can run on any machine with a modern NVIDIA GPU. The entire application is designed to be securely accessible over a private Tailscale mesh network for development or deployed publicly to the web.`For more information about the motivation by Orion as a voice system, see https://github.com/junebug-junie/Orion-Sapienform
Core Architecture

The application is composed of four distinct, containerized services managed by Docker Compose, following modern microservice best practices:

    Voice App (voice-app): The main FastAPI application that serves the user interface, handles WebSocket communication for real-time audio, and orchestrates the other services. It uses Faster-Whisper on the GPU for high-speed, accurate speech-to-text transcription.

    LLM Brain (llm-brain): Runs the Ollama service, which downloads and serves the Mistral 7B Large Language Model. This service acts as the conversational "brain" of the assistant, also leveraging the GPU for fast inference.

    Text-to-Speech (coqui-tts): A robust, self-contained Coqui TTS service that generates high-quality, natural-sounding voice responses. This ensures a consistent and pleasant audio experience for all users.

    Web Proxy (caddy): A production-ready Caddy web server that acts as a reverse proxy. It automatically handles HTTPS, providing the secure connection necessary for browsers to grant microphone access over the network.

Features

    Real-Time Voice Interaction: Press and hold the microphone button to speak and have a continuous, low-latency conversation.

    High-Quality Local AI: All AI processing (Speech-to-Text and LLM) runs locally on your own hardware, ensuring privacy and speed.

    Natural Voice Responses: Integrated Coqui TTS engine provides a consistent, high-quality female voice for the assistant.

    Dynamic UI:

        "Orion's State" Visualizer: A "Winamp-style" geometric visualization that dynamically changes to reflect Orion's current state (idle, listening, processing, speaking).

        Speech Visualizer: A real-time waveform or frequency bar visualizer that syncs with Orion's spoken response.

    Full User Control: A dedicated settings panel allows for real-time adjustment of:

        Orion's Persona: A system prompt to control the AI's personality and behavior.

        LLM Temperature: Adjust the creativity of the model's responses.

        Context Length: Control the conversation's memory.

        Speech Speed: Change the playback rate of the TTS audio.

    Conversation Management: Easily copy the conversation transcript or clear the history.

    Interruptible Speech: A "Stop" button appears while Orion is speaking, allowing you to interrupt long responses.

How to Run This Project

This project is designed to be run in one of two modes: Development (for private access on your Tailscale network) or Production (for public access on the internet).
Prerequisites

    A Linux host with a modern NVIDIA GPU.

    Docker and Docker Compose (v1.29.2+) installed.

    The NVIDIA Container Toolkit installed to allow Docker access to the GPU.

    Tailscale installed and running on the host machine.

First-Time Setup (Common to both modes)

    Place Project Files: Ensure all project files (docker-compose.yml, docker-compose.dev.yml, Dockerfile, etc.) are in a single directory on your host machine.

    Create .env file: Copy the .env.example to .env and fill in your desired Whisper model settings (e.g., WHISPER_MODEL_SIZE=distil-medium.en).

    Build the Voice App Image: Run docker-compose build to build the main voice-app image. This only needs to be done once, or whenever you change main.py or the Dockerfile.

A) Running in Development Mode (Tailscale)

This mode allows you to access Orion from any device on your private Tailscale network.

    Configure Caddy for Dev:
    Edit the Caddyfile.dev file and replace orion-chrysalis with your server's actual Tailscale machine name if it is different.

    Launch the Dev Stack:
    From your project directory, run this command. It merges the base docker-compose.yml with the docker-compose.dev.yml override file.

    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

    Load the LLM Model (One-time setup per volume):

    docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec llm-brain ollama pull mistral

    Connect:
    You can now access the application from any other device on your Tailscale network at:
    https://<your-tailscale-hostname>:8443

    (Note: Your browser will show a one-time security warning because the SSL certificate is self-signed. You must click "Advanced" and "Accept the Risk and Continue".)

B) Running in Production Mode (Public Web App)

This mode deploys Orion to the public internet, accessible from anywhere.

Prerequisites for Production:

    You must have a public domain name (e.g., your-cool-domain.com).

    You must have a DNS "A" record pointing a subdomain (e.g., orion) to the public IP address of your chrysalis server.

    Your internet router must have port forwarding rules for ports 80 and 443 pointing to your chrysalis server's local IP address.

    Your chrysalis server's firewall must allow traffic on ports 80 and 443 (sudo ufw allow 80/tcp, sudo ufw allow 443/tcp).

Deployment Steps:

    Configure Caddy for Prod:
    Edit the Caddyfile.prod file (currently open in the Canvas) and replace orion.your-cool-domain.com with your actual public domain.

    Launch the Prod Stack:
    This command merges the base docker-compose.yml with the docker-compose.prod.yml override file.

    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    Load the LLM Model (One-time setup per volume):

    docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec llm-brain ollama pull mistral

    Go Live:
    You can now access your application from anywhere in the world at your secure, public domain:
    https://orion.your-cool-domain.com

Switching Environments

You cannot run both dev and prod at the same time. To switch, you must first tear down the running environment.

To stop the dev environment:

docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

To stop the prod environment:

docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
