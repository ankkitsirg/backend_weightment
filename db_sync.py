import pyodbc
import requests
import time
import logging

logging.basicConfig(
    filename="db_sync.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_PATH = r"D:\client\Abhijay\Kesar weight system\Kesar weight system ver 1.1\bin\Debug\Database\DbWeightSoftware.mdb"
TABLE_NAME = "tblWeightMentEntry" 
CLOUD_API_URL = "https://backend-weightment.onrender.com/api/new-entry"
CLOUD_LAST_ID_URL = "https://backend-weightment.onrender.com/api/last-id"
POLL_INTERVAL = 5 

def fetch_last_id_from_server():
    """Continuously asks the cloud server for the highest ID it currently has."""
    try:
        response = requests.get(CLOUD_LAST_ID_URL)
        if response.status_code == 200:
            return response.json().get("last_id", 0)
    except Exception as e:
        logging.error(f"Could not reach server to get last ID: {e}")
    
    # If the server is unreachable (e.g., waking up from sleep), return None
    return None

def poll_database():
    # 1. Ask the server where we left off EVERY 5 seconds
    server_last_id = fetch_last_id_from_server()
    
    if server_last_id is None:
        logging.debug("Server is unreachable. Waiting for next polling cycle...")
        return

    conn_str = rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB_PATH};"
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 2. Ask MS Access for anything newer than what the server just reported
        query = f"SELECT * FROM {TABLE_NAME} WHERE ID > ? ORDER BY ID ASC"
        cursor.execute(query, server_last_id)
        
        columns = [column[0] for column in cursor.description]
        new_records = False
        
        for row in cursor.fetchall():
            entry_data = dict(zip(columns, row))
            response = requests.post(CLOUD_API_URL, json=entry_data)
            
            if response.status_code == 200:
                logging.info(f"Successfully synced ID: {entry_data['ID']}")
                new_records = True
            else:
                logging.error(f"Failed to sync ID: {entry_data['ID']} - Status {response.status_code}")
                # Stop processing this batch so we don't skip records on a server error
                break 
                
        if not new_records:
            logging.debug(f"Server is up to date at ID {server_last_id}. Waiting...")
            
        conn.close()
        
    except Exception as e:
        logging.error(f"Database connection or execution error: {e}")

if __name__ == "__main__":
    logging.info("--- Starting Continuous MS Access to FastAPI sync service ---")
    
    while True:
        poll_database()
        time.sleep(POLL_INTERVAL)