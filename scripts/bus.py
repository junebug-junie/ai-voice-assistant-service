import logging
import os
import redis
import json

logger = logging.getLogger("orion-bus")

class OrionBus:
    def __init__(self, url=None, enabled=None):
        # Defaults from env if not provided
        self.url = url or os.getenv("ORION_BUS_URL", "redis://localhost:6379")
        self.enabled = (
            str(enabled).lower() == "true"
            if enabled is not None
            else os.getenv("ORION_BUS_ENABLED", "false").lower() == "true"
        )

        self.client = None
        if self.enabled:
            try:
                self.client = redis.Redis.from_url(self.url, decode_responses=True)
                self.client.ping()
                logger.info(f"Connected to Orion bus at {self.url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis bus at {self.url}: {e}")
                self.client = None
                self.enabled = False
        else:
            logger.info("Orion bus disabled (ORION_BUS_ENABLED=false).")

    def publish(self, channel, message: dict):
        if not self.enabled or not self.client:
            return
        try:
            self.client.publish(channel, json.dumps(message))
            logger.info(f"Published to {channel}: {message}")
        except Exception as e:
            logger.error(f"Publish error on {channel}: {e}")
