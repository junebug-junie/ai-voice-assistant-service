import os
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import numpy as np
from faster_whisper import WhisperModel
import requests
import json

# --- Configuration ---
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Read configuration from environment variables ---
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
LLM_URL = os.getenv("LLM_URL")

# --- Pre-startup Sanity Checks ---
static_dir = "static"
templates_dir = "templates"
if not os.path.exists(static_dir):
    logger.info(f"'{static_dir}' directory not found, creating it.")
    os.makedirs(static_dir)
if not os.path.exists(templates_dir):
    logger.error(f"CRITICAL: The '{templates_dir}' directory was not found. The application cannot start.")

# Global variable for the Whisper model
model = None

# --- FastAPI Application Setup ---
app = FastAPI()

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Model Loading ---
@app.on_event("startup")
async def startup_event():
    """Loads the Whisper model on application startup."""
    global model
    try:
        logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}' on device '{WHISPER_DEVICE}' with compute type '{WHISPER_COMPUTE_TYPE}'")
        model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        logger.info("Whisper model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
        model = None

# --- HTML Template Loading ---
html_content = "<html><body><h1>Error: templates/index.html not found</h1></body></html>"
try:
    with open(os.path.join(templates_dir, "index.html"), "r") as f:
        html_content = f.read()
except FileNotFoundError:
    logger.error(f"CRITICAL: Could not read 'index.html' from '{templates_dir}' directory.")

# --- API Endpoints ---
@app.get("/")
async def get():
    """Serves the main HTML page."""
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/health")
async def health():
    """Health check endpoint for Docker."""
    return {"status": "ok", "whisper_model_loaded": model is not None}

# --- FINAL, HYPER-ROBUST WebSocket Handler ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles the WebSocket connection with defensive error checking."""
    await websocket.accept()
    logger.info("WebSocket connection accepted.")
    
    if not model:
        logger.error("WebSocket connection aborted: Whisper model is not loaded.")
        await websocket.send_json({"error": "Whisper model not loaded on server."})
        await websocket.close()
        return

    try:
        while True:
            message = await websocket.receive()
            # This is the crucial new logging line
            logger.info(f"RAW_MESSAGE_RECEIVED: {message}")

            # Safely get the message type
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                code = message.get('code', 1000)
                logger.info(f"Client disconnected with code: {code}")
                break

            # Safely get the text data from the message
            data = message.get("text")
            if data is not None:
                if data == "EOS":
                    logger.info("End of audio stream received.")
                    continue

                # --- Start processing the audio data ---
                audio_bytes = base64.b64decode(data)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                segments, _ = model.transcribe(audio_np, beam_size=5)
                transcribed_text = " ".join([segment.text for segment in segments]).strip()

                if transcribed_text:
                    logger.info(f"Transcribed: '{transcribed_text}'")
                    await websocket.send_json({"transcript": transcribed_text})

                    # --- Call the LLM ---
                    logger.info(f"Sending prompt to LLM: '{transcribed_text}'")
                    try:
                        llm_payload = {
                            "model": "mistral",
                            "prompt": transcribed_text,
                            "stream": False
                        }
                        response = requests.post(LLM_URL, json=llm_payload, timeout=60)
                        response.raise_for_status()
                        
                        llm_data = response.json()
                        llm_response_text = llm_data.get("response", "No response text found.")
                        
                        logger.info(f"LLM Response: '{llm_response_text}'")
                        await websocket.send_json({"llm_response": llm_response_text})

                    except requests.exceptions.RequestException as e:
                        logger.error(f"Error calling LLM: {e}")
                        await websocket.send_json({"error": f"Could not connect to LLM: {e}"})
                    except Exception as e:
                        logger.error(f"An unexpected error occurred with the LLM call: {e}", exc_info=True)
                        await websocket.send_json({"error": "An unexpected error occurred with the LLM."})
                # --- End LLM Call ---
            else:
                # This will log if the browser sends a message that isn't text (e.g., bytes)
                logger.warning(f"Received a WebSocket message without a 'text' field: {message}")

    except Exception as e:
        logger.error(f"A critical error occurred in the WebSocket main loop: {e}", exc_info=True)
    finally:
        if not websocket.client_state == 'DISCONNECTED':
            await websocket.close()
        logger.info("WebSocket connection resources cleaned up.")

