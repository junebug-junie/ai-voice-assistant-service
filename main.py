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
import tempfile # Import the tempfile module

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

# --- FINAL, CONVERSATIONAL WebSocket Handler ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles a persistent WebSocket connection for a full conversation."""
    await websocket.accept()
    logger.info("WebSocket connection accepted. Ready for conversation.")
    
    if not model:
        logger.error("WebSocket connection aborted: Whisper model is not loaded.")
        await websocket.send_json({"error": "Whisper model not loaded on server."})
        await websocket.close()
        return

    try:
        # --- FIX: Loop to handle multiple interactions in one session ---
        while True:
            # We expect a text message containing the complete base64 audio
            base64_data = await websocket.receive_text()
            logger.info("Received complete audio file from client.")

            audio_bytes = base64.b64decode(base64_data)
            
            transcribed_text = ""
            # Use tempfile to safely handle the audio data
            with tempfile.NamedTemporaryFile(delete=True, suffix=".ogg") as temp_audio_file:
                temp_audio_file.write(audio_bytes)
                temp_audio_file.flush()

                logger.info(f"Transcribing audio from temporary file: {temp_audio_file.name}")
                segments, _ = model.transcribe(temp_audio_file.name, beam_size=5)
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
            else:
                logger.warning("Transcription resulted in empty text.")
                await websocket.send_json({"llm_response": "I'm sorry, I didn't catch that. Could you please speak again?"})

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed cleanly by client.")
    except Exception as e:
        logger.error(f"A critical error occurred in the WebSocket main loop: {e}", exc_info=True)
    finally:
        # This block now runs only when the loop is exited (i.e., client disconnects)
        try:
            if not websocket.client_state == 'DISCONNECTED':
                await websocket.close()
        except RuntimeError as e:
            if "Unexpected ASGI message 'websocket.close'" in str(e):
                logger.info("Gracefully handled a redundant close message.")
            else:
                raise e
        logger.info("WebSocket connection resources cleaned up.")

