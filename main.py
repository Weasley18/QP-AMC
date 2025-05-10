from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import Database
from typing import List, Optional
import os
import shutil

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

db = Database("eduplatform.db")

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

class UserCreate(BaseModel):
    name: str
    email: str
    role: str  # student or teacher

class QuizQuestionCreate(BaseModel):
    question_text: str
    correct_option: str
    options: List[str]

@app.post("/users/")
def create_user(user: UserCreate):
    user_id = db.add_user(user.name, user.email, user.role)
    if user_id:
        return {"user_id": user_id}
    else:
        raise HTTPException(status_code=400, detail="User already exists")

@app.get("/users/{user_id}")
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

@app.post("/documents/")
async def upload_document(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    source_type: str = Form(...)
):
    # Validate source_type
    if source_type not in ["handwritten", "text"]:
        raise HTTPException(status_code=400, detail="Source type must be 'handwritten' or 'text'")
    
    # Save the file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Add document to database
    document_id = db.add_document(user_id, file_path, source_type)
    
    return {"document_id": document_id, "file_path": file_path}

@app.post("/quizzes/")
def create_quiz(document_id: int):
    quiz_id = db.create_quiz(document_id)
    return {"quiz_id": quiz_id}

@app.post("/quizzes/{quiz_id}/questions/")
def add_quiz_question(quiz_id: int, question: QuizQuestionCreate):
    question_id = db.add_quiz_question(
        quiz_id, 
        question.question_text, 
        question.correct_option, 
        question.options
    )
    return {"question_id": question_id}

@app.post("/quiz-attempts/")
def create_quiz_attempt(quiz_id: int, user_id: int):
    attempt_id = db.record_quiz_attempt(quiz_id, user_id)
    return {"attempt_id": attempt_id}

@app.post("/quiz-attempts/{attempt_id}/responses/")
def add_response(
    attempt_id: int, 
    question_id: int, 
    selected_option: str
):
    # Check if the answer is correct
    is_correct = False
    # You would need to implement the logic to check if the answer is correct
    # For now, we'll just set it to False
    
    db.record_attempt_response(attempt_id, question_id, selected_option, is_correct)
    return {"status": "response recorded", "is_correct": is_correct} 