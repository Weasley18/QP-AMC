from database import Database# Create database instance
db = Database('database.db')

# Add a user
user_id = db.add_user('John Doe', 'john@example.com', 'student')

# Add a document
doc_id = db.add_document(user_id, 'path/to/file.pdf', 'handwritten', 'Document content...')

# Create a quiz
quiz_id = db.create_quiz(doc_id)

# Add a question to the quiz
question_id = db.add_quiz_question(
    quiz_id,
    'What is the capital of France?',
    'Paris',
    ['London', 'Paris', 'Berlin', 'Madrid']
)

# Record a quiz attempt
attempt_id = db.record_quiz_attempt(quiz_id, user_id)

# Record a response
db.record_attempt_response(attempt_id, question_id, 'Paris', True)

# Close the database connection when done
db.close()
