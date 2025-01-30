import time
import os
import shutil
import json
from typing import Optional, Dict, Any
from pymongo.errors import PyMongoError
from datetime import datetime
import threading
import logging
from bson import ObjectId

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_manager.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('SyncManager')

class MongoSyncManager:
    def __init__(self, local_storage, mongo_client, sync_interval: int = 300):
        """Initialize the sync manager."""
        self.local_storage = local_storage
        self.mongo_client = mongo_client
        self.sync_interval = sync_interval
        self.sync_thread = None
        self.upload_thread = None
        self.is_running = False
        
        # Create necessary directories
        for dir_path in ['temp_storage', 'logs', 'database']:
            os.makedirs(dir_path, exist_ok=True)

    def _sync_loop(self):
        """Main synchronization loop."""
        while self.is_running:
            try:
                self.sync_all()
                # Cleanup old synced records after 30 days
                self.local_storage.cleanup_old_records(days=30)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            time.sleep(self.sync_interval)

    def _upload_retry_loop(self):
        """Loop for retrying failed file uploads."""
        while self.is_running:
            try:
                self._process_failed_uploads()
            except Exception as e:
                logger.error(f"Error in upload retry loop: {e}")
            time.sleep(self.sync_interval)

    def start(self):
        """Start both sync and upload threads."""
        self.is_running = True
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self._sync_loop)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        # Start upload thread
        self.upload_thread = threading.Thread(target=self._upload_retry_loop)
        self.upload_thread.daemon = True
        self.upload_thread.start()
        
        logger.info("Sync Manager started successfully")

    def stop(self):
        """Stop all background threads."""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join()
        if self.upload_thread:
            self.upload_thread.join()
        logger.info("Sync Manager stopped")

    def sync_all(self):
        """Synchronize all unsynced records."""
        self._sync_predictions()
        self._sync_donations()

    def _prepare_prediction_for_mongo(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare prediction data for MongoDB insertion."""
        # Create a copy to avoid modifying the original
        mongo_pred = pred.copy()
        
        # Remove SQLite-specific fields
        mongo_pred.pop('id', None)
        mongo_pred.pop('is_synced', None)
        mongo_pred.pop('mongo_id', None)
        mongo_pred.pop('error_message', None)

        # Convert timestamp string to datetime if needed
        if isinstance(mongo_pred.get('timestamp'), str):
            mongo_pred['timestamp'] = datetime.fromisoformat(
                mongo_pred['timestamp'].replace('Z', '+00:00')
            )

        # Handle symptoms - ensure it's a list
        if isinstance(mongo_pred.get('symptoms'), str):
            try:
                mongo_pred['symptoms'] = json.loads(mongo_pred['symptoms'])
            except json.JSONDecodeError:
                mongo_pred['symptoms'] = []
        elif mongo_pred.get('symptoms') is None:
            mongo_pred['symptoms'] = []

        return mongo_pred

    def _prepare_donation_for_mongo(self, don: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare donation data for MongoDB insertion."""
        # Create a copy to avoid modifying the original
        mongo_don = don.copy()
        
        # Remove SQLite-specific fields
        mongo_don.pop('id', None)
        mongo_don.pop('is_synced', None)
        mongo_don.pop('mongo_id', None)
        mongo_don.pop('error_message', None)

        # Convert date string to datetime if needed
        if isinstance(mongo_don.get('date'), str):
            mongo_don['date'] = datetime.fromisoformat(
                mongo_don['date'].replace('Z', '+00:00')
            )

        return mongo_don

    def _sync_predictions(self):
        """Sync unsynced predictions to MongoDB."""
        predictions = self.local_storage.get_unsynced_predictions()
        for pred in predictions:
            try:
                # Remove SQLite-specific fields and prepare for MongoDB
                mongo_pred = self._prepare_prediction_for_mongo(pred)
                local_id = pred['id']

                # Insert into MongoDB
                result = self.mongo_client.predictions.insert_one(mongo_pred)
                
                # Mark as synced in local storage
                self.local_storage.mark_prediction_synced(local_id, str(result.inserted_id))
                logger.info(f"Synced prediction with local ID {local_id} to MongoDB with ID {result.inserted_id}")
                
            except PyMongoError as e:
                error_msg = f"Failed to sync prediction with local ID {pred.get('id')}: {str(e)}"
                logger.error(error_msg)
                self.local_storage.update_sync_error("predictions", pred['id'], error_msg)

    def _sync_donations(self):
        """Sync unsynced donations to MongoDB."""
        donations = self.local_storage.get_unsynced_donations()
        for don in donations:
            try:
                # Prepare donation for MongoDB
                mongo_don = self._prepare_donation_for_mongo(don)
                local_id = don['id']

                # Insert into MongoDB
                result = self.mongo_client.donations.insert_one(mongo_don)
                
                # Mark as synced in local storage
                self.local_storage.mark_donation_synced(local_id, str(result.inserted_id))
                logger.info(f"Synced donation with local ID {local_id} to MongoDB with ID {result.inserted_id}")
                
            except PyMongoError as e:
                error_msg = f"Failed to sync donation with local ID {don.get('id')}: {str(e)}"
                logger.error(error_msg)
                self.local_storage.update_sync_error("donations", don['id'], error_msg)

    def _process_failed_uploads(self):
        """Process any failed file uploads."""
        failed_uploads = self.local_storage.get_unsynced_predictions()  # You might want to create a separate table for failed uploads
        for upload in failed_uploads:
            try:
                # Implement retry logic here
                # This could include re-uploading files to a cloud storage
                # or retrying MongoDB file uploads
                pass
            except Exception as e:
                logger.error(f"Error processing failed upload: {e}")

    def sync_single_prediction(self, local_id: int) -> Optional[str]:
        """Sync a single prediction to MongoDB immediately."""
        pred = self.local_storage.get_prediction_by_id(local_id)
        if not pred:
            return None

        try:
            mongo_pred = self._prepare_prediction_for_mongo(pred)
            result = self.mongo_client.predictions.insert_one(mongo_pred)
            self.local_storage.mark_prediction_synced(local_id, str(result.inserted_id))
            logger.info(f"Synced single prediction {local_id} to MongoDB with ID {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            error_msg = f"Failed to sync prediction {local_id}: {str(e)}"
            logger.error(error_msg)
            self.local_storage.update_sync_error("predictions", local_id, error_msg)
            return None

    def sync_single_donation(self, local_id: int) -> Optional[str]:
        """Sync a single donation to MongoDB immediately."""
        don = self.local_storage.get_donation_by_id(local_id)
        if not don:
            return None

        try:
            mongo_don = self._prepare_donation_for_mongo(don)
            result = self.mongo_client.donations.insert_one(mongo_don)
            self.local_storage.mark_donation_synced(local_id, str(result.inserted_id))
            logger.info(f"Synced single donation {local_id} to MongoDB with ID {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            error_msg = f"Failed to sync donation {local_id}: {str(e)}"
            logger.error(error_msg)
            self.local_storage.update_sync_error("donations", local_id, error_msg)
            return None

    def handle_sync_error(self, record_type: str, local_id: int, error: Exception):
        """Handle synchronization errors."""
        error_msg = str(error)
        logger.error(f"Sync error for {record_type} {local_id}: {error_msg}")
        self.local_storage.update_sync_error(record_type, local_id, error_msg)