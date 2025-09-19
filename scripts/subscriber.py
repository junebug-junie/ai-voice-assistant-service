import os
import redis
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("subscriber")

REDIS_URL = os.getenv("ORION_BUS_URL", "redis://redis:6379")

def main():
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    pubsub.psubscribe("orion.voice.*")

    logger.info(f"Subscribed to orion.voice.* on {REDIS_URL}")
    try:
        for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except Exception:
                    data = message["data"]
                logger.info(f"{channel}: {data}")
    except KeyboardInterrupt:
        logger.info("Subscriber stopped.")

if __name__ == "__main__":
    main()
