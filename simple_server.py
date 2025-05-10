from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from database import Database
from typing import List, Optional
import os
import shutil
import uvicorn

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to database
db = Database("eduplatform.db")

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Define models
class UserCreate(BaseModel):
    name: str
    email: str
    role: str  # student or teacher

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("user_creation.html")

# API endpoints
@app.post("/api/users/")
def create_user(user: UserCreate):
    user_id = db.add_user(user.name, user.email, user.role)
    if user_id:
        return {"user_id": user_id}
    else:
        raise HTTPException(status_code=400, detail="User already exists")

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    user = db.get_user(user_id)
    if user:
        return {
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "role": user[3],
            "created_at": user[4]
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Run server
if __name__ == "__main__":
    print("Server running at http://localhost:8000")
    print("Access the user creation form at: http://localhost:8000/")
    uvicorn.run(app, host="0.0.0.0", port=8000) 