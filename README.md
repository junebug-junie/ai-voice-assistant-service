# Orion AI Voice System

This service is a production-grade, self-hosted voice AI assistant. It leverages a multi-container Docker architecture to create a scalable, high-performance system that can run on any machine with a modern NVIDIA GPU. The entire application is designed to be securely accessible over a Tailscale mesh network.

For more information about the motivation by Orion as a voice system, see https://github.com/junebug-junie/Orion-Sapienform

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
Prerequisites

    A Linux host with a modern NVIDIA GPU.

    Docker and Docker Compose (v1.29.2+) installed.

    The NVIDIA Container Toolkit installed to allow Docker access to the GPU.

    Tailscale installed and running on the host machine.

Setup & Installation

    Clone or place all project files (docker-compose.yml, Dockerfile, main.py, .env, etc.) into a single directory on your host machine.

    Ensure you have a templates subdirectory containing the index.html file.

    Configure your environment: Create a .env file with the desired Whisper model settings (e.g., WHISPER_MODEL_SIZE=distil-medium.en).

    Configure Caddy: Edit the Caddyfile and replace orion-chrysalis with your server's actual Tailscale machine name.

The "Nuke and Rebuild" Protocol

This is the definitive method to ensure a clean, fresh start. Run these commands from the root of your project directory:

1. Tear Down and Remove Everything:
This command stops all services, removes the containers, and deletes the persistent data volumes.

docker-compose down --volumes

2. Build and Launch Fresh:
This command rebuilds the voice-app image and then creates and starts all four containers in the background.

docker-compose up -d --build

3. Load the LLM Model (One-Time Setup):
This command downloads the Mistral 7B model into the llm-brain's persistent volume.

docker-compose exec llm-brain ollama pull mistral

Accessing the Application

Once the services are running, you can access the Orion Voice AI from any other device on your Tailscale network by navigating to:

https://<your-tailscale-hostname>:8443

The first time you connect, your browser will show a security warning because the SSL certificate is self-signed. You must click "Advanced..." and "Accept the Risk and Continue". The application will then load and be fully functional.
