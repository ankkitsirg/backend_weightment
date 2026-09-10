import pyodbc
import requests
import time
import os
import logging

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    filename="db_sync.log",          # All logs will be saved to this file
    level=logging.INFO,              # INFO logs successes/errors. (Use logging.DEBUG to see 'Waiting' messages)
    format="%(asctime)s - %(levelname)s - %(message)s" # Adds a timestamp to every log
)

# --- CONFIGURATION ---
DB_PATH = r"D:\client\Abhijay\Kesar weight system\Kesar weight system ver 1.1\bin\Debug\Database\DbWeightSoftware.mdb"
TABLE_NAME = "tblWeightMentEntry" 
CLOUD_API_URL = "https://ankiitpythonanywhere.pythonanywhere.com/api/new-entry"
TRACKER_FILE = "last_processed_id.txt"
POLL_INTERVAL = 5 
# ---------------------

def get_last_id():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            return int(f.read().strip() or 0)
    return 0

def update_last_id(last_id):
    with open(TRACKER_FILE, 'w') as f:
        f.write(str(last_id))

def bootstrap_last_100():
    if os.path.exists(TRACKER_FILE):
        return 

    logging.info("No tracker file found. Bootstrapping the latest 100 records...")
    conn_str = rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB_PATH};"
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        query = f"SELECT TOP 100 * FROM {TABLE_NAME} ORDER BY ID DESC"
        cursor.execute(query)
        
        columns = [column[0] for column in cursor.description]
        records = cursor.fetchall()
        
        if not records:
            logging.info("Database is empty. Nothing to bootstrap.")
            conn.close()
            return
            
        records.reverse()
        highest_id = 0
        
        for row in records:
            entry_data = dict(zip(columns, row))
            response = requests.post(CLOUD_API_URL, json=entry_data)
            
            if response.status_code == 200:
                highest_id = entry_data['ID']
        
        if highest_id > 0:
            update_last_id(highest_id)
            logging.info(f"Successfully bootstrapped 100 records. Now tracking from ID: {highest_id}")
            
        conn.close()
    except Exception as e:
        logging.error(f"Bootstrap error: {e}")

def poll_database():
    conn_str = rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB_PATH};"
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        last_id = get_last_id()
        
        query = f"SELECT * FROM {TABLE_NAME} WHERE ID > ?"
        cursor.execute(query, last_id)
        
        columns = [column[0] for column in cursor.description]
        new_records = False
        
        for row in cursor.fetchall():
            entry_data = dict(zip(columns, row))
            response = requests.post(CLOUD_API_URL, json=entry_data)
            
            if response.status_code == 200:
                logging.info(f"Successfully synced ID: {entry_data['ID']}")
                last_id = entry_data['ID']
                update_last_id(last_id)
                new_records = True
            else:
                logging.error(f"Failed to sync ID: {entry_data['ID']} - Server returned status {response.status_code}")
                
        if not new_records:
            # Set to DEBUG so it doesn't spam your log file every 5 seconds
            logging.debug("No new entries found. Waiting...")
            
        conn.close()
        
    except Exception as e:
        logging.error(f"Database connection or execution error: {e}")

if __name__ == "__main__":
    logging.info("--- Starting MS Access to FastAPI sync service ---")
    
    bootstrap_last_100()
    
    while True:
        poll_database()
        time.sleep(POLL_INTERVAL)