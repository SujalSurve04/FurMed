import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/local_storage.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('LocalStorage')

class LocalStorageHandler:
    def __init__(self, db_path: str = 'database/local_storage.db'):
        """Initialize local storage with SQLite."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.initialize_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        """Execute a SQLite query safely."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return None

    def initialize_db(self):
        """Create necessary tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Predictions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_name TEXT,
                        pet_name TEXT,
                        pet_gender TEXT,
                        pet_type TEXT,
                        disease TEXT,
                        full_animal_image_path TEXT,
                        disease_image_path TEXT,
                        predicted_image_path TEXT,
                        timestamp TEXT,
                        symptoms TEXT,
                        mongo_id TEXT,
                        is_synced INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                ''')
                
                # Donations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS donations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        donor_name TEXT,
                        donation_email TEXT,
                        paypal_email TEXT,
                        phone TEXT,
                        address TEXT,
                        amount_usd REAL,
                        amount_inr REAL,
                        currency TEXT,
                        exchange_rate REAL,
                        status TEXT,
                        transaction_id TEXT,
                        date TEXT,
                        invoice_path TEXT,
                        mongo_id TEXT,
                        is_synced INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Database tables initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def save_prediction(self, data: Dict[str, Any]) -> Optional[int]:
        """Save prediction data to local SQLite database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if 'symptoms' in data and isinstance(data['symptoms'], list):
                    data['symptoms'] = json.dumps(data['symptoms'])
                
                query = '''
                    INSERT INTO predictions (
                        owner_name, pet_name, pet_gender, pet_type, disease,
                        full_animal_image_path, disease_image_path, predicted_image_path,
                        timestamp, symptoms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                values = (
                    data.get('owner_name'),
                    data.get('pet_name'),
                    data.get('pet_gender'),
                    data.get('pet_type'),
                    data.get('disease'),
                    data.get('full_animal_image_path'),
                    data.get('disease_image_path'),
                    data.get('predicted_image_path'),
                    data.get('timestamp', datetime.now().isoformat()),
                    data.get('symptoms')
                )
                
                cursor.execute(query, values)
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error saving prediction to local storage: {e}")
            return None

    def save_donation(self, data: Dict[str, Any]) -> Optional[int]:
        """Save donation data to local SQLite database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    INSERT INTO donations (
                        donor_name, donation_email, paypal_email, phone, address,
                        amount_usd, amount_inr, currency, exchange_rate, status,
                        transaction_id, date, invoice_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                values = (
                    data.get('donor_name'),
                    data.get('donation_email'),
                    data.get('paypal_email'),
                    data.get('phone'),
                    data.get('address'),
                    data.get('amount_usd'),
                    data.get('amount_inr'),
                    data.get('currency'),
                    data.get('exchange_rate'),
                    data.get('status'),
                    data.get('transaction_id'),
                    data.get('date'),
                    data.get('invoice_path')
                )
                
                cursor.execute(query, values)
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error saving donation to local storage: {e}")
            return None

    def get_prediction_by_id(self, local_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific prediction by its local ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM predictions WHERE id = ?', (local_id,))
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    if data.get('symptoms'):
                        try:
                            data['symptoms'] = json.loads(data['symptoms'])
                        except json.JSONDecodeError:
                            data['symptoms'] = []
                    return data
                return None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving prediction: {e}")
            return None

    def get_unsynced_predictions(self) -> List[Dict[str, Any]]:
        """Retrieve predictions that haven't been synced to MongoDB."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM predictions 
                    WHERE is_synced = 0 AND error_message IS NULL
                    ORDER BY timestamp ASC
                ''')
                results = [dict(row) for row in cursor.fetchall()]
                for result in results:
                    if result.get('symptoms'):
                        try:
                            result['symptoms'] = json.loads(result['symptoms'])
                        except json.JSONDecodeError:
                            result['symptoms'] = []
                return results
        except sqlite3.Error as e:
            logger.error(f"Error retrieving unsynced predictions: {e}")
            return []

    def get_unsynced_donations(self) -> List[Dict[str, Any]]:
        """Retrieve donations that haven't been synced to MongoDB."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM donations 
                    WHERE is_synced = 0 AND error_message IS NULL
                    ORDER BY date ASC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving unsynced donations: {e}")
            return []

    def mark_prediction_synced(self, local_id: int, mongo_id: str):
        """Mark a prediction as synced with MongoDB."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE predictions 
                    SET is_synced = 1, mongo_id = ?, error_message = NULL
                    WHERE id = ?
                ''', (mongo_id, local_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking prediction as synced: {e}")

    def mark_donation_synced(self, local_id: int, mongo_id: str):
        """Mark a donation as synced with MongoDB."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE donations 
                    SET is_synced = 1, mongo_id = ?, error_message = NULL
                    WHERE id = ?
                ''', (mongo_id, local_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking donation as synced: {e}")

    def update_sync_error(self, table: str, local_id: int, error_message: str):
        """Update error message for failed sync attempts."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE {table} 
                    SET error_message = ?
                    WHERE id = ?
                ''', (error_message, local_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating sync error: {e}")

    def get_recent_predictions(self, limit: int = 10) -> Tuple[List[Dict[str, Any]], int, float]:
        """Get recent predictions with pagination info."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute('SELECT COUNT(*) as count FROM predictions')
                total_count = cursor.fetchone()['count']
                
                # Get success rate
                cursor.execute('''
                    SELECT COUNT(*) as correct_count 
                    FROM predictions 
                    WHERE is_correct = 1
                ''')
                correct_count = cursor.fetchone()['correct_count']
                success_rate = (correct_count / total_count * 100) if total_count > 0 else 0

                # Get recent predictions
                cursor.execute('''
                    SELECT * FROM predictions 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                results = []
                for row in cursor.fetchall():
                    data = dict(row)
                    if data.get('symptoms'):
                        try:
                            data['symptoms'] = json.loads(data['symptoms'])
                        except json.JSONDecodeError:
                            data['symptoms'] = []
                    results.append(data)
                
                return results, total_count, success_rate
                
        except sqlite3.Error as e:
            logger.error(f"Error getting recent predictions: {e}")
            return [], 0, 0.0

    def get_recent_donations(self, limit: int = 10) -> Tuple[List[Dict[str, Any]], int, float]:
        """Get recent donations with pagination info."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count and sum
                cursor.execute('''
                    SELECT COUNT(*) as count, COALESCE(SUM(amount_inr), 0) as total 
                    FROM donations
                ''')
                result = cursor.fetchone()
                total_count = result['count']
                total_amount = result['total']
                
                # Get recent donations
                cursor.execute('''
                    SELECT * FROM donations 
                    ORDER BY date DESC 
                    LIMIT ?
                ''', (limit,))
                donations = [dict(row) for row in cursor.fetchall()]
                
                return donations, total_count, total_amount
                
        except sqlite3.Error as e:
            logger.error(f"Error getting recent donations: {e}")
            return [], 0, 0.0

    def cleanup_old_records(self, days: int = 30):
        """Clean up old records that have been successfully synced."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM predictions 
                    WHERE is_synced = 1 
                    AND timestamp < ?
                ''', (cutoff_date,))
                cursor.execute('''
                    DELETE FROM donations 
                    WHERE is_synced = 1 
                    AND date < ?
                ''', (cutoff_date,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error during cleanup: {e}")

    def update_prediction_feedback(self, local_id: int, is_correct: bool, correct_label: Optional[str] = None) -> bool:
        """Update feedback for a prediction."""
        try:
            update_query = '''
                UPDATE predictions 
                SET is_correct = ?
                {}
                WHERE id = ?
            '''
            
            if correct_label:
                update_query = update_query.format(", correct_label = ?")
                params = (is_correct, correct_label, local_id)
            else:
                update_query = update_query.format("")
                params = (is_correct, local_id)

            cursor = self.execute_query(update_query, params)
            return cursor is not None and cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error updating prediction feedback: {e}")
            return False
                        
                        