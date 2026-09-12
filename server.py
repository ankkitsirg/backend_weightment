from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "entries.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as file:
        try:
            received_entries = json.load(file)
        except json.JSONDecodeError:
            received_entries = []
else:
    received_entries = []

 # --- Endpoint: Login ---
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    
    if username == "admin" and password == "1234":
        return {"success": True, "message": "Login successful"}
    
    # Returns a 401 status code which triggers the "response.ok === false" check in React Native
    return JSONResponse(
        status_code=401, 
        content={"message": "Incorrect username or password"}
    )   

@app.get("/api/download-json")
def download_json():
    if os.path.exists(DATA_FILE):
        return FileResponse(path=DATA_FILE, filename="entries.json", media_type="application/json")
    return {"error": "File not found or server just restarted"}

# --- Endpoint: Tell the client where to start ---
@app.get("/api/last-id")
def get_last_id():
    if not received_entries:
        return {"last_id": 0}
    
    # Find the maximum ID currently stored in memory
    max_id = max((entry.get("ID", 0) for entry in received_entries), default=0)
    return {"last_id": max_id}

@app.post("/api/new-entry")
async def receive_entry(request: Request):
    data = await request.json()
    incoming_id = data.get("ID")
    
    # ---  CHECK: Prevent duplicates ---
    if any(entry.get("ID") == incoming_id for entry in received_entries):
        return {"status": "ignored", "message": f"ID {incoming_id} already exists"}

    received_entries.append(data)
    
    if len(received_entries) > 100:
        received_entries.pop(0)
        
    with open(DATA_FILE, "w") as file:
        json.dump(received_entries, file, indent=4)
        
    print(f"--> Received new entry ID: {incoming_id}")
    return {"status": "success", "message": "Data received and saved to JSON"}

@app.get("/api/entries")
def get_entries():
    return received_entries[-100:][::-1]

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)