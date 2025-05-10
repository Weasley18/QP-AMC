# Edumate API

A RESTful API for Edumate, an intelligent educational platform that allows users to upload documents, create summaries, generate quizzes, and track learning progress.

## Features

- User management (students and teachers)
- Document uploads and summary generation
- Quiz creation and attempt tracking
- Question paper generation with multiple modes
- Learning progress tracking

## Setup and Installation

1. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

2. Run the API server:
```bash
uvicorn main:app --reload
```

3. Run the Streamlit application:
```bash
streamlit run app.py
```

4. Access the Streamlit UI at http://localhost:8501

## API Endpoints

### Users

- `POST /users/` - Create a new user
- `GET /users/{user_id}` - Get user details

### Documents

- `POST /documents/` - Upload a document
- `POST /summaries/` - Create document summary

### Quizzes

- `POST /quizzes/` - Create a quiz for a document
- `POST /quizzes/{quiz_id}/questions/` - Add a question to a quiz
- `POST /quiz-attempts/` - Start a quiz attempt
- `POST /quiz-attempts/{attempt_id}/responses/` - Record a response to a quiz question

### Question Papers

- `POST /question-papers/` - Generate a question paper with specified settings

## Database Structure

Edumate uses SQLite for data storage with the following tables:

- Users
- Documents
- Summaries
- Quizzes and Questions
- Quiz Attempts and Responses
- Question Papers
- Revision Queue

## Example Usage

### Creating a User

```bash
curl -X 'POST' \
  'http://localhost:8000/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "role": "student"
  }'
```

### Uploading a Document

```bash
curl -X 'POST' \
  'http://localhost:8000/documents/' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@path/to/document.pdf' \
  -F 'user_id=1' \
  -F 'source_type=text'
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 