import os
import sqlite3
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from local_storage import LocalStorageHandler
from sync_manager import MongoSyncManager
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/db_config.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DBConfig')

class DatabaseConfig:
    def __init__(self, mongo_uri: str):
        self.mongo_uri = mongo_uri
        self.local_storage = None
        self.mongo_client = None
        self.sync_manager = None
        self.db = None
        self.predictions_coll = None
        self.donations_coll = None
        self.is_mongo_available = False
        self.db_path = os.path.join('database', 'local_storage.db')

    def get_sqlite_connection(self):
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        """Initialize both local and MongoDB connections."""
        # Initialize local storage
        try:
            self.local_storage = LocalStorageHandler('database/local_storage.db')
            logger.info("Local storage initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing local storage: {e}")
            raise

        # Try to connect to MongoDB with a shorter timeout
        if self.mongo_uri:
            try:
                self.mongo_client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                self.db = self.mongo_client["fur-med"]
                self.predictions_coll = self.db["predictions"]
                self.donations_coll = self.db["donations"]
                
                # Test MongoDB connection
                self.mongo_client.server_info()
                self.is_mongo_available = True
                logger.info("MongoDB connection established successfully")

                # Initialize sync manager
                self.sync_manager = MongoSyncManager(self.local_storage, self.db)
                self.sync_manager.start()
                logger.info("Sync manager started successfully")

            except Exception as e:
                logger.warning(f"MongoDB connection failed: {e}. Operating in local-only mode.")
                self.is_mongo_available = False
                self.mongo_client = None
                self.db = None
                self.predictions_coll = None
                self.donations_coll = None
        else:
            logger.info("No MongoDB URI provided. Operating in local-only mode.")
            self.is_mongo_available = False

    def save_prediction(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Save prediction to storage system."""
        try:
            # Always save to local storage first
            local_id = self.local_storage.save_prediction(data)
            if not local_id:
                return False, "Failed to save to local storage", None

            # If MongoDB is available, try to sync immediately
            if self.is_mongo_available and self.sync_manager:
                try:
                    mongo_id = self.sync_manager.sync_single_prediction(local_id)
                    if mongo_id:
                        return True, "Saved and synced to MongoDB", mongo_id
                    return True, "Saved locally, sync pending", str(local_id)
                except Exception as e:
                    logger.error(f"MongoDB sync error: {e}")
                    return True, "Saved locally, sync failed", str(local_id)
            
            return True, "Saved locally", str(local_id)

        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
            return False, f"Error saving prediction: {str(e)}", None

    def save_donation(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Save donation to storage system."""
        try:
            # Always save to local storage first
            local_id = self.local_storage.save_donation(data)
            if not local_id:
                return False, "Failed to save to local storage", None

            # If MongoDB is available, try to sync immediately
            if self.is_mongo_available and self.sync_manager:
                try:
                    mongo_id = self.sync_manager.sync_single_donation(local_id)
                    if mongo_id:
                        return True, "Saved and synced to MongoDB", mongo_id
                    return True, "Saved locally, sync pending", str(local_id)
                except Exception as e:
                    logger.error(f"MongoDB sync error: {e}")
                    return True, "Saved locally, sync failed", str(local_id)
            
            return True, "Saved locally", str(local_id)

        except Exception as e:
            logger.error(f"Error saving donation: {e}")
            return False, f"Error saving donation: {str(e)}", None

    def get_predictions(self, page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], int, float]:
        """Get paginated predictions from available storage."""
        try:
            if self.is_mongo_available:
                skip = (page - 1) * per_page
                total = self.predictions_coll.count_documents({})
                predictions = list(
                    self.predictions_coll.find({})
                    .sort("timestamp", -1)
                    .skip(skip)
                    .limit(per_page)
                )
                
                total_correct = self.predictions_coll.count_documents({"is_correct": True})
                success_rate = (total_correct / total * 100) if total > 0 else 0
                
                return predictions, total, success_rate
            else:
                return self.local_storage.get_recent_predictions(limit=per_page)
                
        except Exception as e:
            logger.error(f"Error fetching predictions: {e}")
            return [], 0, 0.0

    def get_donations(self, page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], int, float]:
        """Get paginated donations from available storage."""
        try:
            if self.is_mongo_available:
                skip = (page - 1) * per_page
                total = self.donations_coll.count_documents({})
                donations = list(
                    self.donations_coll.find({})
                    .sort("date", -1)
                    .skip(skip)
                    .limit(per_page)
                )
                
                pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount_inr"}}}]
                result = list(self.donations_coll.aggregate(pipeline))
                total_amount = result[0]["total"] if result else 0
                
                return donations, total, total_amount
            else:
                return self.local_storage.get_recent_donations(limit=per_page)
                
        except Exception as e:
            logger.error(f"Error fetching donations: {e}")
            return [], 0, 0.0

    def cleanup(self):
        """Cleanup database connections and stop sync manager."""
        if self.sync_manager:
            self.sync_manager.stop()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("Database connections cleaned up")