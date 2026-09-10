from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os

app = FastAPI()

# Allow the local HTML file to fetch data from this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "entries.json"

# 1. Load existing data when the server starts (if the file exists)
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as file:
        try:
            received_entries = json.load(file)
        except json.JSONDecodeError:
            received_entries = []  # Fallback if the file is empty or corrupted
else:
    received_entries = []

@app.post("/api/new-entry")
async def receive_entry(request: Request):
    data = await request.json()
    received_entries.append(data)
    
    # Keep only the most recent 100 entries in memory
    if len(received_entries) > 100:
        received_entries.pop(0)
        
    # 2. Save the updated list permanently to the JSON file
    with open(DATA_FILE, "w") as file:
        json.dump(received_entries, file, indent=4)
        
    print(f"--> Received new entry ID: {data.get('ID')}")
    return {"status": "success", "message": "Data received and saved to JSON"}

@app.get("/api/entries")
def get_entries():
    # Returns the list from memory, newest first
    return received_entries[-100:][::-1]

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)