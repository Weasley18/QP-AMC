import base64
import os
import json
import sqlite3
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_from_pdf(pdf_file_path: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please add it to your .env file or set it in your environment.")
        
    client = genai.Client(
        api_key=api_key,
    )

    model = "gemini-2.5-flash-preview-04-17"  # Your specified model

    # Read the PDF file in binary mode
    with open(pdf_file_path, "rb") as f:
        pdf_bytes = f.read()

    # Create a Part from the PDF bytes
    pdf_part = types.Part.from_bytes(mime_type="application/pdf", data=pdf_bytes)

    contents = [
        types.Content(
            role="user",
            parts=[
                pdf_part,
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",  # Changed to application/json as per your system instruction
        system_instruction=[
            types.Part.from_text(text="""You will be given a pdf of notes: Handwritten or Typed.
        Your task is to convert handwritten notes to clear text.
        If the pdf is in typed format, just parse the text.
        The return should be a json file with the fields: subject, topics, text.
        Structure the JSON output with proper readability for formulas and examples."""),
        ],
    )

    print(f"Generating content from PDF: {pdf_file_path} using model {model}")
    full_response = ""
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                print(chunk.text, end="")
                full_response += chunk.text
        
        # After completion, store the result in the database
        store_ocr_result(pdf_file_path, full_response)
        return full_response
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def store_ocr_result(pdf_file_path, json_response):
    """Store the OCR result in the database."""
    try:
        # Parse the JSON response
        data = json.loads(json_response)
        
        # Connect to the database
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # First check if user exists, if not create a default user
        cursor.execute('SELECT user_id FROM users WHERE email = ?', ('default@example.com',))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute('''
                INSERT INTO users (name, email, role)
                VALUES (?, ?, ?)
            ''', ('Default User', 'default@example.com', 'student'))
            user_id = cursor.lastrowid
        else:
            user_id = user[0]
        
        # Add document to the database
        cursor.execute('''
            INSERT INTO documents (user_id, original_file_url, source_type, text_content)
            VALUES (?, ?, ?, ?)
        ''', (user_id, pdf_file_path, 'text', data.get('text', '')))
        
        document_id = cursor.lastrowid
        
        # Create a summary with subject and topics
        summary_text = f"Subject: {data.get('subject', 'N/A')}\nTopics: {data.get('topics', 'N/A')}"
        
        cursor.execute('''
            INSERT INTO summaries (document_id, summary_text)
            VALUES (?, ?)
        ''', (document_id, summary_text))
        
        # Mark document as processed
        cursor.execute('''
            UPDATE documents 
            SET processed_at = CURRENT_TIMESTAMP
            WHERE document_id = ?
        ''', (document_id,))
        
        conn.commit()
        print(f"\nSuccessfully stored OCR result in database with document_id: {document_id}")
        
    except json.JSONDecodeError:
        print("Failed to parse JSON from the API response")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error storing OCR result: {e}")

if __name__ == "__main__":
    # Path to your PDF file
    pdf_path = "/Users/chethanar/newamx/QP-AMC/uploads/ada_mod2.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
    else:
        generate_from_pdf(pdf_path)