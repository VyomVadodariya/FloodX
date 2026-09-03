"""
mongodb.py — MongoDB Atlas Integration Layer
============================================

Provides the connection to MongoDB Atlas using PyMongo.
Creates singletons to reuse connections across warm AWS Lambda invocations.
Supports graceful degradation if MongoDB is unreachable (allows local testing
without a cloud database).

Collections:
- sensor_readings (Time Series)
- risk_snapshots
- population_data
- evacuation_graph
- alerts_log
"""

from __future__ import annotations

import os
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ConfigurationError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class FloodXDatabase:
    """MongoDB Singleton Connection Manager."""
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        """Get or initialize the MongoDB database connection."""
        if cls._db is not None:
            return cls._db

        if not PYMONGO_AVAILABLE:
            logger.warning("PyMongo not installed. Running in local mock mode.")
            return None

        uri = os.environ.get("MONGODB_URI")
        if not uri:
            logger.warning("MONGODB_URI not set. Running in local mock mode.")
            return None

        db_name = os.environ.get("MONGODB_DATABASE", "floodx")
        
        try:
            # 3-second timeout for serverless environments
            cls._client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            cls._client.admin.command('ping')
            cls._db = cls._client[db_name]
            logger.info("Successfully connected to MongoDB Atlas.")
            return cls._db
        except (ConnectionFailure, ConfigurationError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            cls._client = None
            return None

    @classmethod
    def store_sensor_reading(cls, reading: dict[str, Any]) -> bool:
        """Store a raw sensor reading into the Time Series collection."""
        db = cls.get_db()
        if not db:
            return False
        
        # MongoDB Time Series requires proper datetime objects
        doc = dict(reading)
        if isinstance(doc.get("timestamp"), str):
            try:
                doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
            except ValueError:
                doc["timestamp"] = datetime.utcnow()
        else:
            doc["timestamp"] = datetime.utcnow()
            
        try:
            db.sensor_readings.insert_one(doc)
            return True
        except Exception as e:
            logger.error(f"Failed to store sensor reading: {e}")
            return False

    @classmethod
    def store_risk_snapshot(cls, snapshot: dict[str, Any]) -> bool:
        """Store an auditable model prediction snapshot."""
        db = cls.get_db()
        if not db:
            return False
            
        doc = dict(snapshot)
        doc["timestamp"] = datetime.utcnow()
        try:
            db.risk_snapshots.insert_one(doc)
            return True
        except Exception as e:
            logger.error(f"Failed to store risk snapshot: {e}")
            return False

    @classmethod
    def store_alert_log(cls, alert: dict[str, Any]) -> bool:
        """Store generated Bedrock alert."""
        db = cls.get_db()
        if not db:
            return False
            
        doc = dict(alert)
        doc["timestamp"] = datetime.utcnow()
        try:
            db.alerts_log.insert_one(doc)
            return True
        except Exception as e:
            logger.error(f"Failed to store alert log: {e}")
            return False

    @classmethod
    def get_recent_history(cls, location_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent time-series history for a location.
        
        Returns oldest-first ordering as expected by feature_engineering.py.
        """
        db = cls.get_db()
        if not db:
            return []
            
        try:
            # Sort descending to get latest, then limit
            cursor = db.sensor_readings.find({"id": location_id}).sort("timestamp", -1).limit(limit)
            history = list(cursor)
            
            # Reverse to return oldest-first sequence for rolling window calculations
            history.reverse()
            
            # Convert ObjectId and datetime back for standard JSON processing
            for h in history:
                if "_id" in h:
                    del h["_id"]
                if isinstance(h.get("timestamp"), datetime):
                    h["timestamp"] = h["timestamp"].isoformat()
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve history for {location_id}: {e}")
            return []
