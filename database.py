import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        
        # Create all tables
        self._create_tables()
        
    def _create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Documents table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_file_url TEXT NOT NULL,
                source_type TEXT CHECK(source_type IN ('handwritten', 'text')) NOT NULL,
                text_content TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Summaries table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
        ''')
        
        # Quizzes table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
        ''')
        
        # Quiz questions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
            )
        ''')
        
        # Question options table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_options (
                option_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id) ON DELETE CASCADE
            )
        ''')
        
        # Quiz attempts table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Attempt responses table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attempt_responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_option TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id) ON DELETE CASCADE
            )
        ''')
        
        # Question papers table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_papers (
                paper_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
        ''')
        
        # Paper questions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS paper_questions (
                paper_question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES question_papers(paper_id) ON DELETE CASCADE
            )
        ''')
        
        # Paper options table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS paper_options (
                paper_option_id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_question_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                FOREIGN KEY (paper_question_id) REFERENCES paper_questions(paper_question_id) ON DELETE CASCADE
            )
        ''')
        
        # Revision queue table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS revision_queue (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                fail_count INTEGER DEFAULT 1,
                last_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                next_review_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_summaries_doc ON summaries(document_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_quizzes_doc ON quizzes(document_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_quiz ON quiz_questions(quiz_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_question ON question_options(question_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_quiz ON quiz_attempts(quiz_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_user ON quiz_attempts(user_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_attempt ON attempt_responses(attempt_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_doc ON question_papers(document_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_revision_user ON revision_queue(user_id)')
        
        self.conn.commit()

    # User operations
    def add_user(self, name, email, role):
        """Add a new user to the database."""
        try:
            self.cursor.execute('''
                INSERT INTO users (name, email, role)
                VALUES (?, ?, ?)
            ''', (name, email, role))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"User with email {email} already exists.")
            return None

    def get_user(self, user_id):
        """Get user details by ID."""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def get_all_users(self):
        """Get all users from the database."""
        self.cursor.execute('SELECT * FROM users ORDER BY user_id')
        return self.cursor.fetchall()

    # Document operations
    def add_document(self, user_id, original_file_url, source_type, text_content=None):
        """Add a new document."""
        self.cursor.execute('''
            INSERT INTO documents (user_id, original_file_url, source_type, text_content)
            VALUES (?, ?, ?, ?)
        ''', (user_id, original_file_url, source_type, text_content))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_document_processed(self, document_id):
        """Mark a document as processed."""
        self.cursor.execute('''
            UPDATE documents 
            SET processed_at = CURRENT_TIMESTAMP
            WHERE document_id = ?
        ''', (document_id,))
        self.conn.commit()

    # Quiz operations
    def create_quiz(self, document_id):
        """Create a new quiz for a document."""
        self.cursor.execute('''
            INSERT INTO quizzes (document_id)
            VALUES (?)
        ''', (document_id,))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_quiz_question(self, quiz_id, question_text, correct_option, options):
        """Add a question to a quiz with its options."""
        self.cursor.execute('''
            INSERT INTO quiz_questions (quiz_id, question_text, correct_option)
            VALUES (?, ?, ?)
        ''', (quiz_id, question_text, correct_option))
        question_id = self.cursor.lastrowid
        
        # Add options for the question
        for option in options:
            self.cursor.execute('''
                INSERT INTO question_options (question_id, option_text)
                VALUES (?, ?)
            ''', (question_id, option))
        
        self.conn.commit()
        return question_id

    # Quiz attempt operations
    def record_quiz_attempt(self, quiz_id, user_id):
        """Record a new quiz attempt."""
        self.cursor.execute('''
            INSERT INTO quiz_attempts (quiz_id, user_id)
            VALUES (?, ?)
        ''', (quiz_id, user_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def record_attempt_response(self, attempt_id, question_id, selected_option, is_correct):
        """Record a response to a quiz question."""
        self.cursor.execute('''
            INSERT INTO attempt_responses (attempt_id, question_id, selected_option, is_correct)
            VALUES (?, ?, ?, ?)
        ''', (attempt_id, question_id, selected_option, is_correct))
        self.conn.commit()

    # Question paper operations
    def create_question_paper(self, document_id, settings=None):
        """Create a new question paper."""
        settings_json = json.dumps(settings) if settings else None
        self.cursor.execute('''
            INSERT INTO question_papers (document_id, settings)
            VALUES (?, ?)
        ''', (document_id, settings_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_paper_question(self, paper_id, question_text, correct_option, options):
        """Add a question to a question paper."""
        self.cursor.execute('''
            INSERT INTO paper_questions (paper_id, question_text, correct_option)
            VALUES (?, ?, ?)
        ''', (paper_id, question_text, correct_option))
        question_id = self.cursor.lastrowid
        
        # Add options for the question
        for option in options:
            self.cursor.execute('''
                INSERT INTO paper_options (paper_question_id, option_text)
                VALUES (?, ?)
            ''', (question_id, option))
        
        self.conn.commit()
        return question_id

    def get_question_paper(self, paper_id):
        """Get question paper details."""
        self.cursor.execute('''
            SELECT qp.*, d.original_file_url, s.summary_text
            FROM question_papers qp
            JOIN documents d ON qp.document_id = d.document_id
            LEFT JOIN summaries s ON d.document_id = s.document_id
            WHERE qp.paper_id = ?
        ''', (paper_id,))
        return self.cursor.fetchone()

    def get_paper_questions(self, paper_id):
        """Get all questions for a paper."""
        self.cursor.execute('''
            SELECT pq.*
            FROM paper_questions pq
            WHERE pq.paper_id = ?
            ORDER BY pq.paper_question_id
        ''', (paper_id,))
        return self.cursor.fetchall()

    def get_paper_question_options(self, paper_question_id):
        """Get options for a paper question."""
        self.cursor.execute('''
            SELECT *
            FROM paper_options
            WHERE paper_question_id = ?
            ORDER BY paper_option_id
        ''', (paper_question_id,))
        return self.cursor.fetchall()

    def get_all_question_papers(self):
        """Get all question papers."""
        self.cursor.execute('''
            SELECT qp.paper_id, d.original_file_url, qp.created_at,
                   (SELECT COUNT(*) FROM paper_questions WHERE paper_id = qp.paper_id) as question_count
            FROM question_papers qp
            JOIN documents d ON qp.document_id = d.document_id
            ORDER BY qp.created_at DESC
        ''')
        return self.cursor.fetchall()

    # Summary operations
    def add_summary(self, document_id, summary_text):
        """Add a summary for a document."""
        self.cursor.execute('''
            INSERT INTO summaries (document_id, summary_text)
            VALUES (?, ?)
        ''', (document_id, summary_text))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_summary(self, document_id):
        """Get summary for a document."""
        self.cursor.execute('''
            SELECT * FROM summaries WHERE document_id = ?
        ''', (document_id,))
        return self.cursor.fetchone()
    
    def get_all_summaries(self):
        """Get all summaries."""
        self.cursor.execute('''
            SELECT s.summary_id, d.document_id, d.original_file_url, s.summary_text, s.generated_at
            FROM summaries s
            JOIN documents d ON s.document_id = d.document_id
            ORDER BY s.generated_at DESC
        ''')
        return self.cursor.fetchall()
    
    def get_documents_with_summaries(self):
        """Get all documents that have summaries."""
        self.cursor.execute('''
            SELECT d.document_id, d.original_file_url, u.name, d.source_type, d.uploaded_at
            FROM documents d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.document_id IN (SELECT document_id FROM summaries)
            ORDER BY d.uploaded_at DESC
        ''')
        return self.cursor.fetchall()

    # Revision queue operations
    def add_to_revision_queue(self, user_id, question_id):
        """Add a question to the revision queue."""
        self.cursor.execute('''
            INSERT INTO revision_queue (user_id, question_id)
            VALUES (?, ?)
        ''', (user_id, question_id))
        self.conn.commit()

    def update_revision_fail_count(self, entry_id):
        """Update the fail count for a revision queue entry."""
        self.cursor.execute('''
            UPDATE revision_queue 
            SET fail_count = fail_count + 1,
                last_failed_at = CURRENT_TIMESTAMP
            WHERE entry_id = ?
        ''', (entry_id,))
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.conn.close() 