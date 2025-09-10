import os
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import base64
import requests
import json
import tempfile
from faster_whisper import WhisperModel
import re

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
LLM_URL = os.getenv("LLM_URL")
TTS_URL = os.getenv("TTS_URL")

# --- Pre-startup Sanity Checks ---
templates_dir = "templates"
model = None
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    global model
    try:
        logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}'...")
        model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        logger.info("Whisper model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}", exc_info=True)

html_content = "<html><body><h1>Error: templates/index.html not found</h1></body></html>"
try:
    with open(os.path.join(templates_dir, "index.html"), "r") as f:
        html_content = f.read()
except FileNotFoundError:
    logger.error(f"CRITICAL: Could not read 'index.html' from '{templates_dir}' directory.")

@app.get("/")
async def get():
    return HTMLResponse(content=html_content, status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted.")
    
    conversation_history = []
    
    if not model:
        await websocket.send_json({"error": "Whisper model not loaded on server."}); await websocket.close(); return

    try:
        while True:
            message_text = await websocket.receive_text()
            message_data = json.loads(message_text)
            
            base64_data = message_data.get("audio")
            temperature = message_data.get("temperature", 0.7)
            context_length = message_data.get("context_length", 10)
            instructions = message_data.get("instructions", "")

            if not base64_data:
                logger.warning("Received WebSocket message without audio data."); continue

            audio_bytes = base64.b64decode(base64_data)
            
            transcribed_text = ""
            with tempfile.NamedTemporaryFile(delete=True, suffix=".ogg") as f:
                f.write(audio_bytes); f.flush()
                segments, _ = model.transcribe(f.name, beam_size=5)
                transcribed_text = " ".join([s.text for s in segments]).strip()

            if transcribed_text:
                logger.info(f"Transcribed: '{transcribed_text}'")
                await websocket.send_json({"transcript": transcribed_text})
                
                if not conversation_history and instructions:
                    conversation_history.append({"role": "system", "content": instructions})
                
                conversation_history.append({"role": "user", "content": transcribed_text})
                
                if len(conversation_history) > context_length:
                    if conversation_history[0]['role'] == 'system':
                         conversation_history = [conversation_history[0]] + conversation_history[-context_length:]
                    else:
                         conversation_history = conversation_history[-context_length:]

                try:
                    llm_payload = {
                        "model": "mistral",
                        "messages": conversation_history,
                        "stream": False,
                        "options": { "temperature": temperature }
                    }
                    logger.info(f"Calling LLM with temperature: {temperature} and context length: {len(conversation_history)}")
                    
                    llm_res = requests.post(LLM_URL, json=llm_payload, timeout=60)
                    llm_res.raise_for_status()
                    
                    llm_message = llm_res.json().get("message", {})
                    llm_text = llm_message.get("content", "").strip()
                    
                    if llm_text:
                        conversation_history.append({"role": "assistant", "content": llm_text})

                    logger.info(f"LLM Response: '{llm_text}'")
                    await websocket.send_json({"llm_response": llm_text})

                    if TTS_URL and llm_text:
                        sentences = re.split(r'(?<=[.!?])\s+', llm_text)
                        for sentence in sentences:
                            clean_sentence = sentence.replace('\n', ' ').strip()
                            if not clean_sentence: continue
                            logger.info(f"Requesting TTS from Coqui for: '{clean_sentence}'")
                            try:
                                # --- FIX: Removed the voice_model parameter ---
                                tts_res = requests.get(TTS_URL, params={"text": clean_sentence}, timeout=60)
                                tts_res.raise_for_status()
                                audio_wav_bytes = tts_res.content
                                audio_base64 = base64.b64encode(audio_wav_bytes).decode('utf-8')
                                await websocket.send_json({"audio_response": audio_base64})
                                logger.info("Successfully sent TTS audio chunk to client.")
                            except requests.exceptions.RequestException as e:
                                logger.error(f"Error calling Coqui TTS service: {e}")
                                await websocket.send_json({"error": "TTS service failed."}); break
                    else:
                        logger.warning("TTS_URL not set or LLM response was empty. Skipping audio response.")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error calling LLM: {e}")
                    await websocket.send_json({"error": "LLM service failed."})
            else:
                logger.warning("Transcription resulted in empty text.")
                await websocket.send_json({"llm_response": "I didn't catch that."})
    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    except Exception as e:
        logger.error(f"A critical error occurred: {e}", exc_info=True)
    finally:
        logger.info("WebSocket connection closed.")

