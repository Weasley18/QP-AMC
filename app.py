import streamlit as st
import requests
import json
from database import Database
import os
import random
import PyPDF2  # Import PyPDF2 for PDF text extraction
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv
from summerize import generate_summary  # Import from summerize.py (note the spelling)
from Qgen import generate_quiz, save_quiz_to_file  # Import quiz generation functions
from chat_interface import create_chatbot_ui  # Import chatbot UI

# Load environment variables from .env file
load_dotenv()

# Set page config
st.set_page_config(
    page_title="Edumate",
    page_icon="📚",
    layout="centered"
)

# Add custom CSS for the entire application
st.markdown("""
<style>
/* Main app styling */
.main {
    background-color: #121212;
    color: #f0f0f0;
}

/* Header styling */
h1, h2, h3 {
    color: #4da6ff;
    font-weight: 600;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    border-radius: 8px 8px 0px 0px;
    padding: 10px 16px;
    background-color: #333;
    border: none;
    color: #f0f0f0;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background-color: #1e88e5 !important;
    color: white !important;
}

/* Card styling */
.card {
    background-color: #1e1e1e;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    border-left: 4px solid #4da6ff;
}

/* Button styling */
.stButton>button {
    border-radius: 6px;
    padding: 4px 20px;
    background-color: #1e88e5;
    color: white;
    border: none;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #0d47a1;
    color: white;
}

/* Form styling */
.stForm {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

/* Input fields */
div[data-baseweb="input"] {
    border-radius: 6px;
}

div[data-baseweb="select"] {
    border-radius: 6px;
}

div[data-baseweb="base-input"] {
    background-color: #333;
}

/* Alert/info box styling */
.stAlert {
    background-color: #1a237e;
    border-radius: 8px;
}

/* File uploader styling */
.uploadedFile {
    background-color: #333;
    border-radius: 6px;
    padding: 10px;
}

/* Expander styling */
.streamlit-expanderHeader {
    background-color: #333;
    border-radius: 6px;
}

/* Success/error/warning indicators */
.success {
    background-color: #004d40;
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
}

.error {
    background-color: #b71c1c;
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
}

.warning {
    background-color: #e65100;
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
}

/* Code display */
.stCodeBlock {
    border-radius: 8px;
    background-color: #2c2c2c;
}

/* Slider styling */
.stSlider {
    margin-bottom: 20px;
}

/* Table styling */
.dataframe {
    background-color: #2c2c2c;
    border-radius: 8px;
}

.dataframe th {
    background-color: #1e88e5;
    color: white;
    text-align: center;
}

/* Selectbox styling */
div[data-baseweb="select"] > div {
    background-color: #333;
    color: white;
}

/* Footer section */
.footer {
    text-align: center;
    margin-top: 50px;
    padding: 20px;
    border-top: 1px solid #333;
    color: #999;
}
</style>
""", unsafe_allow_html=True)

# Initialize database connection
db = Database("edumate.db")

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None

# OCR Function using Google Gemini API
def ocr_pdf_with_gemini(pdf_file_path: str):
    """
    Process a PDF file with Google Gemini OCR and store results in the database.
    Returns the JSON response from the API.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        st.error("GEMINI_API_KEY environment variable not set. Please add it to your .env file.")
        return None
        
    client = genai.Client(
        api_key=api_key,
    )

    model = "gemini-2.5-flash-preview-04-17"

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
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""You will be given a pdf of notes: Handwritten or Typed.
        Your task is to convert handwritten notes to clear text.
        If the pdf is in typed format, just parse the text.
        The return should be a json file with the following structure:
        {
            "subject": "The main subject of the document",
            "topics": ["Topic 1", "Topic 2", "Topic 3"],
            "text": "The full extracted text content",
            "metadata": {
                "document_type": "handwritten or typed",
                "language": "detected language",
                "pages": "number of pages"
            },
            "sections": [
                {
                    "title": "Section title if available",
                    "content": "Content of this section"
                }
            ]
        }
        Ensure proper JSON formatting with indentation for readability."""),
        ],
    )

    try:
        st.info(f"Processing PDF with {model}. This may take a few minutes...")
        
        # Create a placeholder for streaming output
        output_placeholder = st.empty()
        full_response = ""
        
        # Stream the response
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                full_response += chunk.text
                # Update the placeholder with the current response
                output_placeholder.text(full_response)
        
        # Try to parse the JSON response
        try:
            json_data = json.loads(full_response)
            
            # Standardize the JSON structure
            standardized_json = {
                "subject": json_data.get("subject", "Unknown"),
                "topics": json_data.get("topics", []),
                "text": json_data.get("text", ""),
                "metadata": json_data.get("metadata", {
                    "document_type": "unknown",
                    "language": "unknown",
                    "pages": "unknown"
                }),
                "sections": json_data.get("sections", [])
            }
            
            # Format the JSON with proper indentation for display
            formatted_json = json.dumps(standardized_json, indent=2)
            
            return standardized_json
        except json.JSONDecodeError:
            st.error("Failed to parse JSON from the API response.")
            st.code(full_response[:1000] + ("..." if len(full_response) > 1000 else ""))
            return None
            
    except Exception as e:
        st.error(f"An error occurred during OCR processing: {str(e)}")
        return None

# Function to store OCR results in the database
def store_ocr_result(user_id, pdf_file_path, ocr_data):
    """
    Store OCR results in the database.
    Returns the document ID.
    """
    try:
        # Add document to the database
        document_id = db.add_document(
            user_id=user_id, 
            original_file_url=pdf_file_path, 
            source_type='text', 
            text_content=ocr_data.get('text', '')
        )
        
        # Mark document as processed
        db.cursor.execute('''
            UPDATE documents 
            SET processed_at = CURRENT_TIMESTAMP
            WHERE document_id = ?
        ''', (document_id,))
        
        db.conn.commit()
        return document_id
        
    except Exception as e:
        st.error(f"Error storing OCR result: {str(e)}")
        return None

# Function to create a summary using the Gemini API
def create_summary_for_document(document_id):
    """
    Create a summary for a document using the Gemini API.
    Returns the summary_id if successful, None otherwise.
    """
    try:
        # Get document details from database
        document = db.cursor.execute('''
            SELECT document_id, text_content, original_file_url 
            FROM documents
            WHERE document_id = ?
        ''', (document_id,)).fetchone()
        
        if not document or not document[1]:  # If no document or no text content
            st.error("No text content found for this document")
            return None
            
        # Extract subject and topics from OCR data if available
        ocr_data = {}
        text_content = document[1]
        
        # Try to extract subject and topics from text content
        # This is assuming the OCR result is stored as JSON in the text_content field
        try:
            if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                ocr_data = json.loads(text_content)
                # If text is in JSON format, get the text field
                if 'text' in ocr_data:
                    text_content = ocr_data.get('text', '')
        except:
            # If not JSON, use the text as is
            pass
            
        # Generate summary using summerize.py
        summary_result = generate_summary(
            text_content,
            subject=ocr_data.get('subject', None),
            topics=ocr_data.get('topics', None)
        )
        
        if summary_result:
            # Format summary for storage based on summerize.py output format
            # The format is expected to be different from summarize.py
            formatted_summary = ""
            
            # Check if we have a topics list or dictionary
            if isinstance(summary_result, dict):
                # Create a better structured JSON summary format
                structured_summary = {
                    "document_id": document_id,
                    "summary": summary_result.get("summary", ""),
                    "topics": []
                }
                
                if "topics" in summary_result and isinstance(summary_result["topics"], list):
                    # Handle topics as a list of objects with name and content
                    topic_list = []
                    for topic in summary_result.get("topics", []):
                        if isinstance(topic, dict) and "name" in topic and "content" in topic:
                            topic_list.append({
                                "name": topic["name"],
                                "content": topic["content"]
                            })
                            formatted_summary += f"## {topic['name']}\n\n{topic['content']}\n\n"
                        else:
                            topic_list.append({"name": str(topic), "content": ""})
                            formatted_summary += f"- {topic}\n"
                    
                    structured_summary["topics"] = topic_list
                    formatted_summary = "# Summary\n\n" + summary_result.get("summary", "") + "\n\n# Topics\n\n" + formatted_summary
                else:
                    # Handle top-level keys as topics
                    topic_list = []
                    formatted_summary += "# Summary\n\n" + summary_result.get("summary", "") + "\n\n# Topics\n\n"
                    
                    for key, value in summary_result.items():
                        if key != "summary" and key != "topics":
                            topic_list.append({
                                "name": key,
                                "content": value
                            })
                            formatted_summary += f"## {key}\n\n{value}\n\n"
                    
                    structured_summary["topics"] = topic_list
            else:
                # If it's just a text string, create a simple structure
                structured_summary = {
                    "document_id": document_id,
                    "summary": str(summary_result),
                    "topics": []
                }
                formatted_summary = str(summary_result)
            
            # Store the structured JSON in the database along with formatted text
            summary_id = db.add_summary(document_id, formatted_summary)
            
            # Optionally, you can also store the structured JSON separately
            # This would require a database schema update
            # db.add_structured_summary(document_id, json.dumps(structured_summary))
            
            return summary_id
        else:
            st.error("Failed to generate summary")
            return None
            
    except Exception as e:
        st.error(f"Error creating summary: {str(e)}")
        return None

# Advanced function to import data from JSON file
def import_json_data(json_file, document_id):
    """
    Import data from a JSON file and store in appropriate database tables.
    This function is designed to be flexible and handle various JSON structures.
    """
    try:
        # Read the JSON file
        content = json_file.read()
        data = json.loads(content)
        
        results = {
            "actions": [],
            "errors": []
        }
        
        # Process JSON data based on keys
        for key, value in data.items():
            key_lower = key.lower()
            
            # Process summary
            if "summary" in key_lower:
                try:
                    if isinstance(value, str) and value.strip():
                        summary_id = db.add_summary(document_id, value)
                        results["actions"].append(f"Added summary (ID: {summary_id})")
                    elif isinstance(value, dict) and "text" in value:
                        summary_id = db.add_summary(document_id, value["text"])
                        results["actions"].append(f"Added summary from '{key}.text' (ID: {summary_id})")
                except Exception as e:
                    results["errors"].append(f"Error adding summary from '{key}': {str(e)}")
            
            # Process quiz/questions
            elif any(term in key_lower for term in ["quiz", "question", "mcq", "test"]):
                try:
                    # Create a new quiz
                    quiz_id = db.create_quiz(document_id)
                    question_count = 0
                    
                    # Extract questions based on structure
                    questions = []
                    
                    if isinstance(value, dict) and "questions" in value:
                        # Format: {"quiz": {"questions": [...]}}
                        questions = value["questions"]
                    elif isinstance(value, list):
                        # Format: {"questions": [...]}
                        questions = value
                        
                    # Process each question
                    for question in questions:
                        if isinstance(question, dict):
                            # Try to extract question components using various possible key names
                            question_text = None
                            correct_option = None
                            options = []
                            
                            # Extract question text
                            for q_key in ["question_text", "question", "text", "stem"]:
                                if q_key in question:
                                    question_text = question[q_key]
                                    break
                                    
                            # Extract correct option
                            for c_key in ["correct_option", "correct", "answer", "correct_answer"]:
                                if c_key in question:
                                    correct_option = question[c_key]
                                    break
                            
                            # Extract options
                            for o_key in ["options", "choices", "answers"]:
                                if o_key in question and isinstance(question[o_key], list):
                                    options = question[o_key]
                                    break
                            
                            # If we have the minimum required components, add the question
                            if question_text and (correct_option or (options and len(options) > 0)):
                                # If correct_option is missing but we have options, use the first option
                                if not correct_option and options:
                                    correct_option = options[0]
                                    
                                # If options are missing but we have correct_option, create a default set
                                if not options and correct_option:
                                    options = [correct_option, "Option 2", "Option 3", "Option 4"]
                                
                                # Ensure correct_option is in options
                                if correct_option not in options:
                                    options.append(correct_option)
                                
                                # Add question to database
                                db.add_quiz_question(quiz_id, question_text, correct_option, options)
                                question_count += 1
                    
                    if question_count > 0:
                        results["actions"].append(f"Added quiz (ID: {quiz_id}) with {question_count} questions")
                    else:
                        # If no questions were added, remove the empty quiz
                        db.cursor.execute("DELETE FROM quizzes WHERE quiz_id = ?", (quiz_id,))
                        db.conn.commit()
                        results["errors"].append(f"No valid questions found in '{key}'")
                        
                except Exception as e:
                    results["errors"].append(f"Error processing '{key}': {str(e)}")
            
            # Process question papers
            elif any(term in key_lower for term in ["paper", "exam", "test", "assessment"]):
                try:
                    # Check if it's a structured question paper object
                    if isinstance(value, dict) and "questions" in value:
                        # Create question paper
                        settings = {}
                        
                        # Extract settings if available
                        if "settings" in value and isinstance(value["settings"], dict):
                            settings = value["settings"]
                        elif "mode" in value:
                            settings["mode"] = value["mode"]
                        elif "difficulty" in value:
                            settings["difficulty"] = value["difficulty"]
                        
                        # Create the question paper
                        paper_id = db.create_question_paper(document_id, settings)
                        question_count = 0
                        
                        # Add questions
                        for question in value["questions"]:
                            if isinstance(question, dict):
                                question_text = None
                                correct_option = None
                                options = []
                                
                                # Extract question components
                                for q_key in ["question_text", "question", "text"]:
                                    if q_key in question:
                                        question_text = question[q_key]
                                        break
                                
                                for c_key in ["correct_option", "correct", "answer"]:
                                    if c_key in question:
                                        correct_option = question[c_key]
                                        break
                                
                                for o_key in ["options", "choices", "answers"]:
                                    if o_key in question and isinstance(question[o_key], list):
                                        options = question[o_key]
                                        break
                                
                                # Add the question if we have the necessary data
                                if question_text and correct_option:
                                    # If options are missing, create dummy options
                                    if not options:
                                        options = [correct_option, "Option 2", "Option 3"]
                                    
                                    # Ensure correct option is in the list
                                    if correct_option not in options:
                                        options.append(correct_option)
                                    
                                    db.add_paper_question(paper_id, question_text, correct_option, options)
                                    question_count += 1
                        
                        if question_count > 0:
                            results["actions"].append(f"Added question paper (ID: {paper_id}) with {question_count} questions")
                        else:
                            # If no questions were added, remove the empty paper
                            db.cursor.execute("DELETE FROM question_papers WHERE paper_id = ?", (paper_id,))
                            db.conn.commit()
                            results["errors"].append(f"No valid questions found in '{key}'")
                    
                except Exception as e:
                    results["errors"].append(f"Error processing question paper from '{key}': {str(e)}")
        
        # If no actions were performed, return error
        if not results["actions"]:
            results["errors"].append("No valid data found in the JSON file. Please check the format.")
        
        return results
    
    except json.JSONDecodeError as e:
        return {"errors": [f"Invalid JSON format: {str(e)}"]}
    except Exception as e:
        return {"errors": [f"Error processing JSON file: {str(e)}"]}

# Define API URL (use the backend API endpoint)
API_URL = "http://localhost:8000/api"

# App title and description
st.title("Edumate")
st.markdown("Your intelligent education platform for document management, quizzes, and interactive learning")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "User Management 👤", 
    "Documents 📄", 
    "Quizzes 📊", 
    "Question Papers 📋",
    "Chatbot 💬"
])

# Helper function to pretty format JSON for display
def format_json_for_display(data):
    """Format JSON data for better display in Streamlit"""
    if isinstance(data, dict):
        # Add CSS styling for boundaries and larger text
        styled_output = """
        <style>
        .topic-container {
            border: 2px solid #4da6ff;
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            background-color: #1e3d59;
        }
        .topic-heading {
            font-size: 22px;
            font-weight: 600;
            color: #8ab4f8;
            margin-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            padding-bottom: 8px;
        }
        .topic-content {
            font-size: 16px;
            line-height: 1.6;
            margin-top: 10px;
        }
        .summary-section {
            font-size: 18px;
            line-height: 1.6;
            margin: 20px 0;
            padding: 15px;
            background-color: rgba(77, 166, 255, 0.1);
            border-radius: 8px;
        }
        .metadata-item {
            font-size: 16px;
            margin: 5px 0;
        }
        .section-header {
            font-size: 24px;
            font-weight: 600;
            color: #4da6ff;
            margin: 25px 0 15px 0;
            border-bottom: 2px solid #4da6ff;
            padding-bottom: 8px;
        }
        </style>
        """
        
        formatted_output = styled_output
        
        # Group keys by categories
        metadata_keys = ["subject", "document_type", "language", "metadata", "pages"]
        content_keys = ["text", "content", "full_text"]
        topic_keys = ["topics", "sections", "key_points", "categories"]
        summary_keys = ["summary"]
        
        # If this is a summary document, reorganize to put topics as headings
        if "topics" in data and any(k in data for k in summary_keys):
            # Start with a document title if subject exists
            if "subject" in data:
                formatted_output += f'<h1 style="color:#8ab4f8;font-size:28px;margin-bottom:20px;">{data["subject"]}</h1>'
            
            # Add the main summary as an introduction section
            if "summary" in data and data["summary"]:
                formatted_output += '<div class="section-header">Overview</div>'
                formatted_output += f'<div class="summary-section">{data["summary"]}</div>'
            
            # Display topics as main sections with their content
            formatted_output += '<div class="section-header">Topics</div>'
            
            topics = data.get("topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    if isinstance(topic, dict):
                        topic_name = topic.get("name", "Untitled Topic")
                        topic_content = topic.get("content", "")
                        
                        formatted_output += f'''
                        <div class="topic-container">
                            <div class="topic-heading">{topic_name}</div>
                            <div class="topic-content">{topic_content}</div>
                        </div>
                        '''
                    else:
                        # Handle simple topic strings
                        formatted_output += f'''
                        <div class="topic-container">
                            <div class="topic-heading">{topic}</div>
                        </div>
                        '''
            
            # Add metadata at the bottom
            metadata_items = [k for k in data.keys() if k in metadata_keys]
            if metadata_items:
                formatted_output += '<div class="section-header">Document Information</div>'
                formatted_output += '<div style="padding:10px;background-color:#1e3d59;border-radius:8px;">'
                for key in metadata_items:
                    value = data[key]
                    if key == "metadata" and isinstance(value, dict):
                        for mk, mv in value.items():
                            formatted_output += f'<div class="metadata-item"><strong>{mk.replace("_", " ").title()}:</strong> {mv}</div>'
                    else:
                        formatted_output += f'<div class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
                formatted_output += '</div>'
            
            return formatted_output
        
        # Standard formatting for other types of data
        # Format metadata section
        metadata_items = [k for k in data.keys() if k in metadata_keys]
        if metadata_items:
            formatted_output += '<div class="section-header">📝 Document Metadata</div>'
            formatted_output += '<div style="padding:10px;background-color:#1e3d59;border-radius:8px;">'
            for key in metadata_items:
                value = data[key]
                if key == "metadata" and isinstance(value, dict):
                    formatted_output += "<details>\n<summary>Metadata Details</summary>\n\n"
                    for mk, mv in value.items():
                        formatted_output += f'<div class="metadata-item"><strong>{mk.replace("_", " ").title()}:</strong> {mv}</div>'
                    formatted_output += "</details>\n"
                else:
                    formatted_output += f'<div class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
            formatted_output += '</div>'
        
        # Format topics section
        topic_items = [k for k in data.keys() if k in topic_keys]
        if topic_items:
            formatted_output += '<div class="section-header">📋 Topics & Categories</div>'
            
            for key in topic_items:
                value = data[key]
                if isinstance(value, list):
                    if key == "sections" and all(isinstance(item, dict) for item in value):
                        for i, section in enumerate(value):
                            formatted_output += f'''
                            <div class="topic-container">
                                <div class="topic-heading">{section.get('title', f'Section {i+1}')}</div>
                                <div class="topic-content">{section.get('content', '')}</div>
                            </div>
                            '''
                    else:
                        formatted_output += f'<div style="font-size:18px;margin-bottom:10px;"><strong>{key.replace("_", " ").title()}:</strong></div>'
                        for i, item in enumerate(value):
                            if isinstance(item, dict) and "name" in item:
                                topic_name = item.get("name", "")
                                topic_content = item.get("content", "")
                                
                                formatted_output += f'''
                                <div class="topic-container">
                                    <div class="topic-heading">{topic_name}</div>
                                    <div class="topic-content">{topic_content}</div>
                                </div>
                                '''
                            else:
                                formatted_output += f'<div class="metadata-item">• {item}</div>'
        
        # Format content section (collapsed by default as it can be long)
        content_items = [k for k in data.keys() if k in content_keys and k not in ["sections"]]
        if content_items:
            formatted_output += '<div class="section-header">📄 Content</div>'
            for key in content_items:
                value = data[key]
                if isinstance(value, str) and len(value) > 200:
                    preview = value[:200] + "..."
                    formatted_output += f"<details>\n<summary style='font-size:18px;'>{key.replace('_', ' ').title()} (Preview)</summary>\n\n"
                    formatted_output += f'<div class="topic-content">{value}</div>'
                    formatted_output += "</details>\n"
                else:
                    formatted_output += f'<div style="font-size:18px;margin-bottom:10px;"><strong>{key.replace("_", " ").title()}:</strong></div>'
                    formatted_output += f'<div class="topic-content">{value}</div>'
        
        # Add other keys that don't fit in categories
        other_keys = [k for k in data.keys() if k not in metadata_keys + topic_keys + content_keys + summary_keys]
        if other_keys:
            formatted_output += '<div class="section-header">⚙️ Other Information</div>'
            for key in other_keys:
                value = data[key]
                if isinstance(value, dict):
                    formatted_output += f"<details>\n<summary style='font-size:18px;'>{key.replace('_', ' ').title()}</summary>\n\n"
                    formatted_output += '<div style="padding:10px;background-color:#1e3d59;border-radius:8px;">'
                    for k, v in value.items():
                        formatted_output += f'<div class="metadata-item"><strong>{k}:</strong> {v}</div>'
                    formatted_output += '</div>'
                    formatted_output += "</details>\n"
                elif isinstance(value, list):
                    formatted_output += f'<div style="font-size:18px;margin-bottom:10px;"><strong>{key.replace("_", " ").title()}:</strong></div>'
                    for item in value:
                        formatted_output += f'<div class="metadata-item">• {item}</div>'
                else:
                    formatted_output += f'<div class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
                    
        return formatted_output
    elif isinstance(data, list):
        # Add styling for lists
        styled_output = """
        <style>
        .list-item {
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px;
            margin: 8px 0;
            font-size: 16px;
            background-color: #1e3d59;
            border-radius: 6px;
        }
        .list-header {
            font-size: 20px;
            font-weight: 600;
            margin: 15px 0 10px 0;
            color: #8ab4f8;
        }
        </style>
        """
        
        formatted_output = styled_output
        
        # Check if it's a list of dictionaries
        if all(isinstance(item, dict) for item in data):
            # Group by common keys
            for i, item in enumerate(data):
                formatted_output += f'<div class="list-header">Item {i+1}</div>'
                formatted_output += '<div style="padding:12px;background-color:#1e3d59;border-radius:8px;margin-bottom:15px;">'
                for key, value in item.items():
                    formatted_output += f'<div class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
                formatted_output += '</div>'
        else:
            # Simple list
            for i, item in enumerate(data):
                formatted_output += f'<div class="list-item">• {item}</div>'
                
        return formatted_output
    else:
        # For simple types, just convert to string with larger font
        return f'<div style="font-size:16px;">{str(data)}</div>'

# ---- USER MANAGEMENT TAB ----
with tab1:
    st.header("User Management")
    
    # User creation form
    with st.expander("Create New User", expanded=True):
        with st.form("user_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            role = st.selectbox("Role", ["student", "teacher"])
            
            submit_button = st.form_submit_button("Create User")
            
            if submit_button:
                if name and email:
                    # Try to create user directly with database
                    try:
                        user_id = db.add_user(name, email, role)
                        if user_id:
                            st.success(f"User created successfully! User ID: {user_id}")
                        else:
                            st.error("User with this email already exists.")
                    except Exception as e:
                        st.error(f"Error creating user: {str(e)}")
                else:
                    st.warning("Please fill all required fields.")
    
    # User listing
    with st.expander("View Users", expanded=True):
        if st.button("Refresh User List"):
            try:
                # Get all users from database
                users = db.get_all_users() if hasattr(db, 'get_all_users') else None
                
                if users and len(users) > 0:
                    # Display user data in a table
                    st.dataframe(
                        data={
                            "ID": [user[0] for user in users],
                            "Name": [user[1] for user in users],
                            "Email": [user[2] for user in users],
                            "Role": [user[3] for user in users],
                            "Created At": [user[4] for user in users]
                        },
                        hide_index=True
                    )
                else:
                    st.info("No users found in the database.")
            except Exception as e:
                st.error(f"Error fetching users: {str(e)}")
                st.info("Note: You need to implement 'get_all_users' method in your Database class")

# ---- DOCUMENTS TAB ----
with tab2:
    st.header("Document Management")
    
    doc_tab1, doc_tab2, doc_tab3 = st.tabs(["Upload Document", "OCR Processing", "Manage Summaries"])
    
    # Upload Document Tab
    with doc_tab1:
        with st.form("document_form"):
            user_id = st.number_input("User ID", min_value=1, step=1)
            source_type = st.selectbox("Document Type", ["handwritten", "text"])
            uploaded_file = st.file_uploader("Upload Document", type=["pdf", "png", "jpg", "txt"])
            
            submit_doc = st.form_submit_button("Upload Document")
            
            if submit_doc and uploaded_file is not None:
                # Save uploaded file
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extract text content if it's a PDF
                text_content = None
                if uploaded_file.name.lower().endswith('.pdf'):
                    with st.spinner("Extracting text from PDF..."):
                        text_content = extract_text_from_pdf(file_path)
                        if text_content:
                            st.success("Successfully extracted text from PDF!")
                        else:
                            st.warning("Could not extract text from PDF. The file might be scanned or image-based.")
                
                # Add document to database
                try:
                    document_id = db.add_document(user_id, file_path, source_type, text_content)
                    st.success(f"Document uploaded successfully! Document ID: {document_id}")
                    
                    if text_content:
                        st.info(f"Extracted {len(text_content.split())} words from the PDF.")
                        with st.expander("Preview Extracted Text"):
                            st.text_area("Extracted Content", text_content[:1000] + 
                                         ("..." if len(text_content) > 1000 else ""), 
                                         height=200, disabled=True)
                    
                    st.info("Now you can add a summary for this document in the 'Manage Summaries' tab.")
                except Exception as e:
                    st.error(f"Error uploading document: {str(e)}")
    
    # OCR Processing Tab
    with doc_tab2:
        st.subheader("OCR Processing with Google Gemini")
        st.markdown("""
        Process PDF documents (including handwritten notes) using Google's Gemini AI.
        The system will extract text, identify subject and topics, and store in the database.
        """)
        
        # User selection
        try:
            users = db.get_all_users()
            if users and len(users) > 0:
                user_options = {f"{user[1]} ({user[2]}, {user[3]})": user[0] for user in users}
                
                selected_user = st.selectbox(
                    "Select User", 
                    options=list(user_options.keys()),
                    help="Select a user to associate with this document",
                    key="ocr_user"
                )
                
                selected_user_id = user_options[selected_user]
                
                # PDF file upload
                uploaded_pdf = st.file_uploader("Upload PDF File for OCR", type=["pdf"], key="ocr_pdf")
                
                if uploaded_pdf is not None:
                    # Display basic file info
                    file_details = {"FileName": uploaded_pdf.name, "FileType": uploaded_pdf.type, "FileSize": f"{uploaded_pdf.size / 1024:.2f} KB"}
                    st.write(file_details)
                    
                    # Save the uploaded file
                    file_path = os.path.join("uploads", uploaded_pdf.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_pdf.getbuffer())
                    
                    st.success(f"PDF saved at: {file_path}")
                    
                    # Process button
                    if st.button("Process with Gemini OCR"):
                        # Run OCR processing
                        with st.spinner("Processing PDF with Gemini AI..."):
                            ocr_result = ocr_pdf_with_gemini(file_path)
                            
                            if ocr_result:
                                st.success("OCR processing completed!")
                                
                                # Store in database
                                document_id = store_ocr_result(selected_user_id, file_path, ocr_result)
                                
                                if document_id:
                                    st.success(f"OCR results stored in database! Document ID: {document_id}")
                                    
                                    # Display results
                                    tabs = st.tabs(["Subject", "Topics", "Text", "Generate Summary"])
                                    
                                    with tabs[0]:
                                        st.subheader("Subject")
                                        st.write(ocr_result.get("subject", "No subject identified"))
                                    
                                    with tabs[1]:
                                        st.subheader("Topics")
                                        topics = ocr_result.get("topics", "No topics identified")
                                        if isinstance(topics, list):
                                            for topic in topics:
                                                st.write(f"• {topic}")
                                        else:
                                            st.write(topics)
                                    
                                    with tabs[2]:
                                        st.subheader("Extracted Text")
                                        text_content = ocr_result.get("text", "No text extracted")
                                        st.text_area("Content", text_content, height=300)
                                        
                                        # Add raw JSON view for developers
                                        with st.expander("View Raw JSON"):
                                            st.json(ocr_result)
                                    
                                    with tabs[3]:
                                        st.subheader("Generate Summary")
                                        st.info("Click the button below to generate a summary for this document.")
                                        
                                        if st.button("Summarize Document"):
                                            with st.spinner("Generating summary..."):
                                                summary_id = create_summary_for_document(document_id)
                                                
                                                if summary_id:
                                                    st.success(f"Summary generated successfully! Summary ID: {summary_id}")
                                                    
                                                    # Get the summary from the database
                                                    summary = db.get_summary(document_id)
                                                    if summary:
                                                        st.markdown("""
                                                        <style>
                                                        .scrollable-summary-box {
                                                            height: 300px;
                                                            overflow-y: auto;
                                                            border: 1px solid #cccccc;
                                                            border-radius: 6px;
                                                            padding: 16px;
                                                            margin: 15px 0;
                                                            background-color: white;
                                                            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                                                        }
                                                        /* Scrollbar styling */
                                                        .scrollable-summary-box::-webkit-scrollbar {
                                                            width: 8px;
                                                        }
                                                        .scrollable-summary-box::-webkit-scrollbar-track {
                                                            background: #f1f1f1;
                                                            border-radius: 4px;
                                                        }
                                                        .scrollable-summary-box::-webkit-scrollbar-thumb {
                                                            background: #888;
                                                            border-radius: 4px;
                                                        }
                                                        .scrollable-summary-box::-webkit-scrollbar-thumb:hover {
                                                            background: #555;
                                                        }
                                                        .summary-content {
                                                            font-size: 16px;
                                                            line-height: 1.6;
                                                            color: #333333;
                                                        }
                                                        .summary-header {
                                                            font-size: 18px;
                                                            font-weight: 600;
                                                            color: #2c5282;
                                                            margin-bottom: 10px;
                                                            padding-bottom: 8px;
                                                            border-bottom: 1px solid #e2e8f0;
                                                        }
                                                        </style>
                                                        """, unsafe_allow_html=True)
                                                        
                                                        st.markdown("## Summary")
                                                        
                                                        # Display the summary with proper markdown in a scrollable box
                                                        st.markdown(f"""
                                                        <div class="summary-header">Generated: {summary[4]}</div>
                                                        <div class="scrollable-summary-box">
                                                            <div class="summary-content">
                                                                {summary[3]}
                                                            </div>
                                                        </div>
                                                        """, unsafe_allow_html=True)
                                                    else:
                                                        st.error("Summary was created but could not be retrieved.")
                            else:
                                st.error("OCR processing failed. Please try again.")
            else:
                st.warning("No users found. Please create a user first.")
        except Exception as e:
            st.error(f"Error in OCR processing: {str(e)}")
    
    # Document Summaries Tab
    with doc_tab3:
        # Display existing documents that need summaries
        st.subheader("Document Summaries")
        
        try:
            # Get all documents from database
            documents = db.cursor.execute('''
                SELECT d.document_id, d.original_file_url, u.name, d.source_type, d.uploaded_at,
                    (SELECT COUNT(*) FROM summaries s WHERE s.document_id = d.document_id) as has_summary
                FROM documents d
                JOIN users u ON d.user_id = u.user_id
                ORDER BY d.uploaded_at DESC
            ''').fetchall()
            
            if documents and len(documents) > 0:
                # Create a dictionary for document selection
                doc_options = {f"Document #{doc[0]}: {os.path.basename(doc[1])} (by {doc[2]})": doc[0] for doc in documents}
                
                selected_doc = st.selectbox(
                    "Select Document", 
                    options=list(doc_options.keys()),
                    help="Select a document to view or generate its summary"
                )
                
                selected_doc_id = doc_options[selected_doc]
                
                # Check if document already has a summary
                existing_summary = db.get_summary(selected_doc_id)
                
                # Get document details for potential JSON formatting
                document = db.cursor.execute('''
                    SELECT document_id, text_content, original_file_url 
                    FROM documents
                    WHERE document_id = ?
                ''', (selected_doc_id,)).fetchone()
                
                # Display document info in a nice card
                if document:
                    st.markdown("""
                    <style>
                    .document-card {
                        background-color: #1e3d59;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0 20px 0;
                    }
                    .summary-card {
                        background-color: #046582;
                        border-radius: 10px;
                        padding: 20px;
                        margin-top: 20px;
                    }
                    .summary-section {
                        margin-top: 15px;
                        padding: 10px;
                        background-color: rgba(255, 255, 255, 0.1);
                        border-radius: 5px;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Format file path for display
                    file_path = document[2]
                    file_name = os.path.basename(file_path)
                    
                    st.markdown(f"""
                    <div class="document-card">
                        <h3>Document Details</h3>
                        <p><strong>File:</strong> {file_name}</p>
                        <p><strong>ID:</strong> {document[0]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if existing_summary:
                    st.success("This document already has a summary!")
                    
                    # Display summary with better formatting
                    st.markdown("""
                    <style>
                    .summary-card {
                        background-color: #046582;
                        border-radius: 10px;
                        padding: 20px;
                        margin-top: 20px;
                    }
                    .scrollable-summary-box {
                        height: 300px;
                        overflow-y: auto;
                        border: 1px solid #cccccc;
                        border-radius: 6px;
                        padding: 16px;
                        margin: 15px 0;
                        background-color: white;
                        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                    }
                    /* Scrollbar styling */
                    .scrollable-summary-box::-webkit-scrollbar {
                        width: 8px;
                    }
                    .scrollable-summary-box::-webkit-scrollbar-track {
                        background: #f1f1f1;
                        border-radius: 4px;
                    }
                    .scrollable-summary-box::-webkit-scrollbar-thumb {
                        background: #888;
                        border-radius: 4px;
                    }
                    .scrollable-summary-box::-webkit-scrollbar-thumb:hover {
                        background: #555;
                    }
                    .summary-content {
                        font-size: 16px;
                        line-height: 1.6;
                        color: #333333;
                    }
                    .summary-header {
                        font-size: 18px;
                        font-weight: 600;
                        color: #2c5282;
                        margin-bottom: 10px;
                        padding-bottom: 8px;
                        border-bottom: 1px solid #e2e8f0;
                    }
                    </style>
                    
                    <div class="summary-card">
                        <h3>Document Summary</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display the summary with proper markdown in a scrollable box
                    st.markdown(f"""
                    <div class="scrollable-summary-box">
                        <div class="summary-content">
                            {existing_summary[2]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add a view raw JSON option for OCR data
                    try:
                        if document and document[1]:
                            text_content = document[1]
                            if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                                with st.expander("View Source Data (JSON)"):
                                    try:
                                        ocr_data = json.loads(text_content)
                                        st.json(ocr_data)
                                    except:
                                        st.text(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                    except Exception as e:
                        st.error(f"Error displaying source data: {e}")
                    
                    if st.button("Regenerate Summary"):
                        with st.spinner("Regenerating summary..."):
                            # Delete old summary
                            db.cursor.execute("DELETE FROM summaries WHERE document_id = ?", (selected_doc_id,))
                            db.conn.commit()
                            
                            # Generate new summary
                            summary_id = create_summary_for_document(selected_doc_id)
                            
                            if summary_id:
                                st.success(f"Summary regenerated successfully! Summary ID: {summary_id}")
                                st.rerun()
                else:
                    st.info("This document doesn't have a summary yet.")
                    
                    if st.button("Generate Summary"):
                        with st.spinner("Generating summary..."):
                            summary_id = create_summary_for_document(selected_doc_id)
                            
                            if summary_id:
                                st.success(f"Summary generated successfully! Summary ID: {summary_id}")
                                
                                # Get the summary from the database
                                summary = db.get_summary(selected_doc_id)
                                if summary:
                                    st.markdown("""
                                    <style>
                                    .scrollable-summary-box {
                                        height: 300px;
                                        overflow-y: auto;
                                        border: 1px solid #cccccc;
                                        border-radius: 6px;
                                        padding: 16px;
                                        margin: 15px 0;
                                        background-color: white;
                                        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                                    }
                                    /* Scrollbar styling */
                                    .scrollable-summary-box::-webkit-scrollbar {
                                        width: 8px;
                                    }
                                    .scrollable-summary-box::-webkit-scrollbar-track {
                                        background: #f1f1f1;
                                        border-radius: 4px;
                                    }
                                    .scrollable-summary-box::-webkit-scrollbar-thumb {
                                        background: #888;
                                        border-radius: 4px;
                                    }
                                    .scrollable-summary-box::-webkit-scrollbar-thumb:hover {
                                        background: #555;
                                    }
                                    .summary-content {
                                        font-size: 16px;
                                        line-height: 1.6;
                                        color: #333333;
                                    }
                                    .summary-header {
                                        font-size: 18px;
                                        font-weight: 600;
                                        color: #2c5282;
                                        margin-bottom: 10px;
                                        padding-bottom: 8px;
                                        border-bottom: 1px solid #e2e8f0;
                                    }
                                    </style>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown("## Summary")
                                    
                                    # Display the summary with proper markdown in a scrollable box
                                    st.markdown(f"""
                                    <div class="summary-header">Generated: {summary[4]}</div>
                                    <div class="scrollable-summary-box">
                                        <div class="summary-content">
                                            {summary[3]}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("Summary was created but could not be retrieved.")
            else:
                st.warning("No documents found. Please upload a document first.")
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
            st.info("Make sure you have uploaded documents first.")
        
        # View all summaries
        st.subheader("All Document Summaries")
        
        # Add the scrollable summary box style once at the section level
        st.markdown("""
        <style>
        .scrollable-summary-box {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 16px;
            margin: 15px 0;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        /* Scrollbar styling */
        .scrollable-summary-box::-webkit-scrollbar {
            width: 8px;
        }
        .scrollable-summary-box::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        .scrollable-summary-box::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        .scrollable-summary-box::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        .summary-content {
            font-size: 16px;
            line-height: 1.6;
            color: #333333;
        }
        .summary-header {
            font-size: 18px;
            font-weight: 600;
            color: #2c5282;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e2e8f0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("Show All Summaries"):
            try:
                summaries = db.get_all_summaries()
                if summaries and len(summaries) > 0:
                    for i, summary in enumerate(summaries):
                        with st.expander(f"Summary #{summary[0]} - Document: {os.path.basename(summary[2])}", expanded=False):
                            # Use the scrollable box for summary content
                            st.markdown(f"""
                            <div class="summary-header">Generated: {summary[4]}</div>
                            <div class="scrollable-summary-box">
                                <div class="summary-content">
                                    {summary[3]}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No summaries found in the database.")
            except Exception as e:
                st.error(f"Error loading summaries: {str(e)}")

# ---- QUIZZES TAB ----
with tab3:
    st.header("Quiz Generation and Taking")
    
    # Add styling for the quiz tab
    st.markdown("""
    <style>
    .quiz-container {
        background-color: #002147;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border-left: 5px solid #4da6ff;
    }
    .quiz-title {
        color: #4da6ff;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .quiz-question {
        background-color: #0a2b5e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 3px solid #3caea3;
    }
    .quiz-option {
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 5px;
        background-color: #1e3d59;
    }
    .quiz-option:hover {
        background-color: #2c5282;
    }
    .quiz-option.selected {
        background-color: #2c5282;
        border-left: 3px solid #ffc107;
    }
    .quiz-option.correct {
        background-color: #004d40;
        border-left: 3px solid #00e676;
    }
    .quiz-option.incorrect {
        background-color: #b71c1c;
        border-left: 3px solid #ff1744;
    }
    .quiz-results {
        background-color: #0a2b5e;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        text-align: center;
    }
    .quiz-score {
        font-size: 24px;
        font-weight: bold;
        color: #4da6ff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create tabs for quiz generation and taking
    quiz_tab1, quiz_tab2 = st.tabs(["Create Quiz", "Take Quiz"])
    
    # Quiz generation tab
    with quiz_tab1:
        st.subheader("Generate Quiz from Document")
        
        try:
            # Get documents with text content
            documents = db.cursor.execute('''
                SELECT d.document_id, d.original_file_url, u.name, d.text_content 
                FROM documents d
                JOIN users u ON d.user_id = u.user_id
                WHERE d.text_content IS NOT NULL
                ORDER BY d.processed_at DESC
            ''').fetchall()
            
            if documents and len(documents) > 0:
                # Format document options nicely
                doc_options = {f"{doc[0]}: {os.path.basename(doc[1])} (by {doc[2]})": doc for doc in documents}
                
                st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
                selected_doc = st.selectbox(
                    "Select Document", 
                    options=list(doc_options.keys()),
                    help="Select a document to generate quiz questions from"
                )
                
                document = doc_options[selected_doc]
                document_id = document[0]
                text_content = document[3]
                
                if text_content:
                    # Number of questions
                    num_questions = st.slider("Number of Questions", min_value=3, max_value=20, value=5, step=1)
                    
                    # Extract topic information
                    topics = ""
                    try:
                        if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                            ocr_data = json.loads(text_content)
                            if 'subject' in ocr_data:
                                topics = ocr_data['subject']
                            if 'topics' in ocr_data:
                                if isinstance(ocr_data['topics'], list):
                                    topics = ", ".join(ocr_data['topics'])
                                else:
                                    topics = ocr_data['topics']
                                if 'subject' in ocr_data:
                                    topics = f"{ocr_data['subject']}: {topics}"
                    except:
                        pass
                    
                    topic_input = st.text_input("Topic/Subject", value=topics, key="topic_input")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                    # Generate Quiz button
                    if st.button("Generate Quiz", type="primary"):
                        with st.spinner("Generating quiz questions..."):
                            # Prepare text content
                            try:
                                if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                                    ocr_data = json.loads(text_content)
                                    if 'text' in ocr_data:
                                        text_content = ocr_data.get('text', '')
                            except:
                                pass
                            
                            # Generate quiz using Qgen.py
                            quiz_data = generate_quiz(text_content, topic_input, num_questions)
                            
                            if quiz_data:
                                # Save quiz to file
                                save_quiz_to_file(quiz_data)
                                st.success(f"Generated {len(quiz_data)} quiz questions!")
                                
                                # Format and display the generated quiz JSON
                                st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
                                st.markdown('<div class="quiz-title">Generated Quiz</div>', unsafe_allow_html=True)
                                
                                # Display the JSON in a better format
                                with st.expander("View Raw JSON", expanded=False):
                                    st.json(quiz_data)
                                
                                # Preview the quiz questions
                                for i, question in enumerate(quiz_data):
                                    st.markdown(f'<div class="quiz-question">', unsafe_allow_html=True)
                                    st.markdown(f"**Q{i+1}.** {question['question']}")
                                    
                                    # Display options
                                    for j, option in enumerate(question['options']):
                                        letter = chr(65 + j)  # A, B, C, D...
                                        is_correct = option == question['answer']
                                        
                                        # Mark correct answers in the preview
                                        if is_correct:
                                            st.markdown(f"**{letter}. {option}** ✓")
                                        else:
                                            st.markdown(f"{letter}. {option}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Direct to take quiz tab
                                st.session_state.show_quiz = True
                                st.info("Quiz generated! Go to 'Take Quiz' tab to start the quiz.")
                            else:
                                st.error("Failed to generate quiz. Please try again.")
                else:
                    st.warning("Selected document has no text content. Please choose another document.")
            else:
                st.warning("No documents found. Please upload a document first.")
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
    
    # Take Quiz tab
    with quiz_tab2:
        st.subheader("Take the Quiz")
        
        # Load quiz data from file
        def load_quiz_data(path="quiz.json"):
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, KeyError):
                    return None
            return None
        
        quiz_data = load_quiz_data()
        
        if quiz_data:
            # Display quiz information
            if isinstance(quiz_data, list) and len(quiz_data) > 0:
                st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
                st.markdown(f'<div class="quiz-title">Quiz with {len(quiz_data)} questions</div>', unsafe_allow_html=True)
                st.info("Select your answer for each question and click Submit when you're finished.")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Create a dict to store user responses
            if "user_responses" not in st.session_state:
                st.session_state.user_responses = {}
            
            # Display questions
            for i, q in enumerate(quiz_data):
                st.markdown(f'<div class="quiz-question">', unsafe_allow_html=True)
                st.markdown(f"**Question {i+1}:** {q['question']}")
                
                # Create radio buttons for options
                option_key = f"quiz_q_{i}"
                st.session_state.user_responses[i] = st.radio(
                    "Choose your answer:", 
                    q["options"],
                    key=option_key,
                    label_visibility="collapsed"  # Hide the label since we show the question above
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Submit button
            if st.button("Submit Answers", key="submit_quiz", type="primary"):
                score = 0
                for i, q in enumerate(quiz_data):
                    correct = q["answer"]
                    chosen = st.session_state.user_responses[i]
                    if correct == chosen:
                        score += 1
            
                # Calculate percentage
                percentage = int((score / len(quiz_data)) * 100)
                
                # Display score with improved formatting
                st.markdown(f"""
                <div class="quiz-results">
                    <div class="quiz-score">Your Score: {score}/{len(quiz_data)} ({percentage}%)</div>
                """, unsafe_allow_html=True)
                
                # Feedback based on score
                if percentage >= 80:
                    st.markdown('<p style="color:#00e676; font-size:18px;">🎉 Excellent work! You\'ve mastered this topic!</p>', unsafe_allow_html=True)
                elif percentage >= 60:
                    st.markdown('<p style="color:#ffc107; font-size:18px;">👍 Good job! You understand most of the material.</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p style="color:#ff5252; font-size:18px;">📚 Keep studying! You\'ll improve with practice.</p>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
                # Show answer review
                st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
                st.markdown('<div class="quiz-title">Review Your Answers</div>', unsafe_allow_html=True)
                
                for i, q in enumerate(quiz_data):
                    correct = q["answer"]
                    chosen = st.session_state.user_responses[i]
                    is_correct = correct == chosen
                    
                    # Create a nicely styled question review
                    st.markdown(f'<div class="quiz-question">', unsafe_allow_html=True)
                    st.markdown(f"**Q{i+1}:** {q['question']}")
                    
                    # Display each option with appropriate styling
                    for option in q['options']:
                        is_user_selected = option == chosen
                        is_correct_option = option == correct
                        
                        if is_user_selected and is_correct_option:
                            # Correct answer selected
                            st.markdown(f'<div class="quiz-option correct">✅ {option} (Your answer - Correct!)</div>', unsafe_allow_html=True)
                        elif is_user_selected and not is_correct_option:
                            # Wrong answer selected
                            st.markdown(f'<div class="quiz-option incorrect">❌ {option} (Your answer - Incorrect)</div>', unsafe_allow_html=True)
                        elif not is_user_selected and is_correct_option:
                            # Correct answer not selected
                            st.markdown(f'<div class="quiz-option correct">✓ {option} (Correct answer)</div>', unsafe_allow_html=True)
                        else:
                            # Regular option
                            st.markdown(f'<div class="quiz-option">{option}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            if st.session_state.get('show_quiz', False):
                st.error("⚠️ Quiz generation failed. Please try again.")
            else:
                st.info("No quiz has been generated yet. Go to the 'Create Quiz' tab to generate a quiz.")

# ---- QUESTION PAPERS TAB ----
with tab4:
    st.header("Question Paper Generation")
    
    # Apply better styling for the question paper generation section
    st.markdown("""
    <style>
    .topic-card {
        background-color: #1e3d59;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .qp-options {
        background-color: #00539c;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .qp-container {
        background-color: #002147;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border-left: 5px solid #ffc13b;
    }
    .qp-title {
        color: #ffc13b;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .qp-question {
        background-color: #0a2b5e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 3px solid #3caea3;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Select document with summary
    try:
        docs_with_summaries = db.get_documents_with_summaries()
        if docs_with_summaries and len(docs_with_summaries) > 0:
            doc_options = {f"{doc[0]}: {os.path.basename(doc[1])} (by {doc[2]})": doc[0] for doc in docs_with_summaries}
            
            st.markdown('<div class="topic-card">', unsafe_allow_html=True)
            selected_doc = st.selectbox(
                "Select Document with Summary", 
                options=list(doc_options.keys()),
                help="Select a document that has a summary to generate a question paper"
            )
            
            selected_doc_id = doc_options[selected_doc]
            
            # Get summary for the selected document
            summary = db.get_summary(selected_doc_id)
            
            if summary:
                st.success("Document summary found!")
                
                with st.expander("View Summary", expanded=False):
                    st.write(summary[2])  # Display the summary text
                
                # Get document text from database
                document = db.cursor.execute('''
                    SELECT text_content FROM documents WHERE document_id = ?
                ''', (selected_doc_id,)).fetchone()
                
                if document and document[0]:
                    text_content = document[0]
                    
                    # Try to extract subject/topics from text content
                    topics = []
                    try:
                        if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                            ocr_data = json.loads(text_content)
                            if 'topics' in ocr_data and isinstance(ocr_data['topics'], list):
                                topics = ocr_data['topics']
                            elif 'topics' in ocr_data:
                                # If topics is a string, split by commas
                                if isinstance(ocr_data['topics'], str):
                                    topics = [t.strip() for t in ocr_data['topics'].split(',')]
                    except:
                        pass
                    
                    # Add a default "All Topics" option
                    if topics:
                        topics = ["All Topics"] + topics
                    else:
                        topics = ["All Topics"]
                    
                    # Topics selection dropdown
                    selected_topics = st.multiselect(
                        "Select Topics to Include",
                        options=topics,
                        default=["All Topics"],
                        help="Select specific topics or 'All Topics' to include everything"
                    )
                    
                    # If user has deselected "All Topics" but not selected anything else, guide them
                    if not selected_topics:
                        st.warning("Please select at least one topic or 'All Topics'")
                        selected_topics = ["All Topics"]  # Default back to All Topics
                    
                    # Filter content based on selected topics
                    filtered_text = text_content
                    if "All Topics" not in selected_topics and topics and len(topics) > 1:
                        try:
                            # Try to extract only the sections related to selected topics
                            # This is a simplified approach - would need more sophistication for actual topic filtering
                            filtered_sections = []
                            
                            # If we have JSON data, try to filter based on topics
                            if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                                ocr_data = json.loads(text_content)
                                if 'text' in ocr_data:
                                    # Extract just the text for now - more sophisticated filtering could be added
                                    filtered_text = ocr_data.get('text', '')
                        except:
                            # Fall back to full text if filtering fails
                            filtered_text = text_content
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Question paper generation modes
                st.markdown('<div class="qp-options">', unsafe_allow_html=True)
                st.subheader("Question Paper Settings")
                
                # Remove the mode selection radio buttons and keep only number of questions
                num_questions = st.slider("Number of Questions", min_value=5, max_value=30, value=10, step=1)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Generate button
                if st.button("Generate Question Paper", type="primary"):
                    with st.spinner("Generating question paper..."):
                        try:
                            # Topic string for Qgen
                            topic_string = ", ".join(selected_topics) if "All Topics" not in selected_topics else "All Topics"
                            
                            # Use the Qgen module to generate questions
                            generated_questions = generate_quiz(filtered_text, topic_string, num_questions)
                            
                            if generated_questions and len(generated_questions) > 0:
                                # Save to file for reference
                                save_quiz_to_file(generated_questions, "question_paper.json")
                                
                                # Display the generated question paper
                                st.markdown('<div class="qp-container">', unsafe_allow_html=True)
                                st.markdown(f'<div class="qp-title">Question Paper ({len(generated_questions)} Questions)</div>', unsafe_allow_html=True)
                                
                                # Format the questions nicely
                                for i, question in enumerate(generated_questions):
                                    st.markdown(f'<div class="qp-question">', unsafe_allow_html=True)
                                    st.markdown(f"**Q{i+1}.** {question['question']}")
                                    
                                    # Display options with letters
                                    for j, option in enumerate(question['options']):
                                        letter = chr(65 + j)  # A, B, C, D...
                                        is_correct = option == question['answer']
                                        
                                        # Only mark correct answer in the admin view
                                        if is_correct:
                                            st.markdown(f"**{letter}. {option}** ✓")
                                        else:
                                            st.markdown(f"{letter}. {option}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Add download capability
                                question_paper_json = json.dumps(generated_questions, indent=2)
                                st.download_button(
                                    label="Download Question Paper (JSON)",
                                    data=question_paper_json,
                                    file_name="question_paper.json",
                                    mime="application/json"
                                )
                                
                                # Create a printable version
                                printable = f"## Question Paper\n\n"
                                for i, question in enumerate(generated_questions):
                                    printable += f"**Q{i+1}.** {question['question']}\n\n"
                                    for j, option in enumerate(question['options']):
                                        letter = chr(65 + j)
                                        printable += f"{letter}. {option}\n"
                                    printable += "\n"
                                
                                st.download_button(
                                    label="Download Printable Version (Markdown)",
                                    data=printable,
                                    file_name="question_paper.md",
                                    mime="text/markdown"
                                )
                            else:
                                st.error("Failed to generate questions. Please try different settings or another document.")
                        except Exception as e:
                            st.error(f"Error generating question paper: {str(e)}")
            else:
                st.warning("Selected document has no summary. Please generate a summary first.")
        else:
            st.warning("No documents with summaries found. Please upload documents and generate summaries first.")
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
    
    # Manage existing question papers
    with st.expander("Manage Existing Question Papers", expanded=False):
        try:
            # List existing question papers
            papers = db.cursor.execute('''
                SELECT p.paper_id, d.document_id, d.original_file_url, p.created_at
                FROM question_papers p
                JOIN documents d ON p.document_id = d.document_id
                ORDER BY p.created_at DESC
            ''').fetchall()
            
            if papers and len(papers) > 0:
                st.subheader("Existing Question Papers")
                for paper in papers:
                    paper_id = paper[0]
                    document_name = os.path.basename(paper[2]) if paper[2] else f"Document {paper[1]}"
                    created_at = paper[3]
                    
                    st.markdown(f"**Paper ID: {paper_id}** - {document_name} (Created: {created_at})")
                    
                    if st.button(f"Delete Paper {paper_id}", key=f"del_paper_{paper_id}"):
                        db.cursor.execute("DELETE FROM question_papers WHERE paper_id = ?", (paper_id,))
                        db.conn.commit()
                        st.success(f"Question paper (ID: {paper_id}) deleted.")
                        st.rerun()
            else:
                st.info("No existing question papers found.")
        except Exception as e:
            st.error(f"Error loading question papers: {str(e)}")

# ---- CHATBOT TAB ----
with tab5:
    st.header("Learning Assistant")
    
    # Create chatbot UI
    create_chatbot_ui()

# Add a footer with version and credit information
st.markdown("""
<div class="footer">
    <p>Edumate - Intelligent Education Platform v1.2.0</p>
    <p>© 2023-2024 Edumate Team. All rights reserved.</p>
    <p>Powered by Gemini, LearnLM, and Streamlit</p>
</div>
""", unsafe_allow_html=True)

# Footer
st.divider()
st.caption("Edumate - Your AI-Powered Education Platform") 