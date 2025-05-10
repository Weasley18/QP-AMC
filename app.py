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

# Load environment variables from .env file
load_dotenv()

# Set page config
st.set_page_config(
    page_title="Edumate",
    page_icon="📚",
    layout="centered"
)

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
        The return should be a json file with the fields: subject, topics, text.
        Structure the JSON output with proper readability for formulas and examples."""),
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
            return json_data
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
                if "topics" in summary_result and isinstance(summary_result["topics"], list):
                    # Format with topics as a list
                    formatted_summary += "# Summary\n\n"
                    if "summary" in summary_result:
                        formatted_summary += f"{summary_result.get('summary', '')}\n\n"
                    
                    formatted_summary += "# Topics\n\n"
                    for topic in summary_result.get("topics", []):
                        if isinstance(topic, dict) and "name" in topic and "content" in topic:
                            formatted_summary += f"## {topic['name']}\n\n{topic['content']}\n\n"
                        else:
                            formatted_summary += f"- {topic}\n"
                else:
                    # Format for topic-content pairs as top-level keys
                    formatted_summary += "# Summary\n\n"
                    
                    # Extract the main summary if it exists
                    if "summary" in summary_result:
                        formatted_summary += f"{summary_result.get('summary', '')}\n\n"
                    
                    # Process other keys as potential topics
                    formatted_summary += "# Topics\n\n"
                    for key, value in summary_result.items():
                        if key != "summary" and key != "topics":
                            formatted_summary += f"## {key}\n\n{value}\n\n"
            else:
                # If it's just text, use it directly
                formatted_summary = str(summary_result)
            
            # Add summary to database
            summary_id = db.add_summary(document_id, formatted_summary)
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
tab1, tab2, tab3, tab4 = st.tabs([
    "User Management 👤", 
    "Documents 📄", 
    "Quizzes 📊", 
    "Question Papers 📋"
])

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
                                                        st.markdown("## Summary")
                                                        st.markdown(summary[2])
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
                
                if existing_summary:
                    st.success("This document already has a summary!")
                    st.subheader("Existing Summary")
                    st.markdown(existing_summary[2])
                    
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
                                    st.markdown("## Generated Summary")
                                    st.markdown(summary[2])
                                else:
                                    st.error("Summary was created but could not be retrieved.")
            else:
                st.warning("No documents found. Please upload a document first.")
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
            st.info("Make sure you have uploaded documents first.")
        
        # View all summaries
        st.subheader("All Document Summaries")
        if st.button("Show All Summaries"):
            try:
                summaries = db.get_all_summaries()
                if summaries and len(summaries) > 0:
                    for i, summary in enumerate(summaries):
                        with st.expander(f"Summary #{summary[0]} - Document: {os.path.basename(summary[2])}", expanded=False):
                            st.markdown(summary[3])
                            st.caption(f"Generated: {summary[4]}")
                else:
                    st.info("No summaries found in the database.")
            except Exception as e:
                st.error(f"Error loading summaries: {str(e)}")

# ---- QUIZZES TAB ----
with tab3:
    st.header("Quiz Management")
    
    # Create quiz form
    with st.expander("Create Quiz", expanded=True):
        with st.form("quiz_form"):
            document_id = st.number_input("Document ID", min_value=1, step=1)
            create_quiz_btn = st.form_submit_button("Create Quiz")
            
            if create_quiz_btn:
                try:
                    quiz_id = db.create_quiz(document_id)
                    st.success(f"Quiz created successfully! Quiz ID: {quiz_id}")
                except Exception as e:
                    st.error(f"Error creating quiz: {str(e)}")
    
    # Add quiz question form
    with st.expander("Add Quiz Question", expanded=False):
        with st.form("question_form"):
            quiz_id = st.number_input("Quiz ID", min_value=1, step=1, key="quiz_question")
            question_text = st.text_area("Question Text")
            correct_option = st.text_input("Correct Option")
            
            options_text = st.text_area("Options (one per line)")
            
            add_question_btn = st.form_submit_button("Add Question")
            
            if add_question_btn:
                if question_text and correct_option and options_text:
                    options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                    
                    if correct_option not in options:
                        options.append(correct_option)
                    
                    try:
                        question_id = db.add_quiz_question(quiz_id, question_text, correct_option, options)
                        st.success(f"Question added successfully! Question ID: {question_id}")
                    except Exception as e:
                        st.error(f"Error adding question: {str(e)}")
                else:
                    st.warning("Please fill all required fields for the question.")

# ---- QUESTION PAPERS TAB ----
with tab4:
    st.header("Question Paper Generation")
    
    # Select document with summary
    try:
        docs_with_summaries = db.get_documents_with_summaries()
        if docs_with_summaries and len(docs_with_summaries) > 0:
            doc_options = {f"{doc[0]}: {os.path.basename(doc[1])} (by {doc[2]})": doc[0] for doc in docs_with_summaries}
            
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
                
                # Question paper generation modes
                st.subheader("Question Paper Mode")
                
                mode = st.radio(
                    "Select Generation Mode",
                    ["Basic Mode", "Advanced Mode", "Exam Mode"],
                    help="Choose the type of question paper to generate"
                )
                
                # Generation options based on mode
                with st.form("question_paper_form"):
                    st.subheader(f"Question Paper Settings - {mode}")
                    
                    if mode == "Basic Mode":
                        num_questions = st.slider("Number of Questions", min_value=5, max_value=20, value=10, step=1)
                        num_options = st.slider("Options per Question", min_value=2, max_value=5, value=4, step=1)
                        difficulty = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Hard"], value="Medium")
                        
                        settings = {
                            "mode": "basic",
                            "num_questions": num_questions,
                            "num_options": num_options,
                            "difficulty": difficulty
                        }
                        
                    elif mode == "Advanced Mode":
                        num_questions = st.slider("Number of Questions", min_value=3, max_value=15, value=8, step=1)
                        include_match_type = st.checkbox("Include Match the Following", value=True)
                        include_true_false = st.checkbox("Include True/False Questions", value=True)
                        include_descriptive = st.checkbox("Include Descriptive Questions", value=False)
                        
                        settings = {
                            "mode": "advanced",
                            "num_questions": num_questions,
                            "include_match_type": include_match_type,
                            "include_true_false": include_true_false,
                            "include_descriptive": include_descriptive
                        }
                        
                    else:  # Exam Mode
                        time_limit = st.slider("Time Limit (minutes)", min_value=30, max_value=180, value=60, step=15)
                        total_marks = st.slider("Total Marks", min_value=20, max_value=100, value=50, step=5)
                        mcq_percentage = st.slider("MCQ Percentage", min_value=0, max_value=100, value=60, step=10)
                        descriptive_percentage = 100 - mcq_percentage
                        
                        st.info(f"Distribution: {mcq_percentage}% MCQs, {descriptive_percentage}% Descriptive")
                        
                        settings = {
                            "mode": "exam",
                            "time_limit": time_limit,
                            "total_marks": total_marks,
                            "mcq_percentage": mcq_percentage,
                            "descriptive_percentage": descriptive_percentage
                        }
                    
                    generate_btn = st.form_submit_button("Generate Question Paper")
                    
                    if generate_btn:
                        try:
                            # Create the question paper
                            paper_id = db.create_question_paper(selected_doc_id, settings)
                            
                            # Simulate question generation based on the summary
                            # In a real application, this would use NLP or AI to generate questions
                            summary_text = summary[2]
                            sentences = [s.strip() for s in summary_text.split('.') if s.strip()]
                            
                            # Generate based on selected mode
                            if mode == "Basic Mode":
                                # Generate random MCQ questions
                                for i in range(min(num_questions, len(sentences))):
                                    if i < len(sentences):
                                        question = f"What does the following refer to: '{sentences[i]}'?"
                                        correct = f"Option {random.randint(1, num_options)}"
                                        options = [f"Option {j}" for j in range(1, num_options+1)]
                                        
                                        db.add_paper_question(paper_id, question, correct, options)
                            
                            elif mode == "Advanced Mode":
                                # Generate mixed question types
                                for i in range(min(num_questions, len(sentences))):
                                    if i < len(sentences):
                                        # Mix of different question types
                                        if i % 3 == 0 and include_match_type:
                                            question = "Match the following terms with their definitions:"
                                            correct = "A-1, B-2, C-3, D-4"
                                            options = ["A-1, B-2, C-3, D-4", "A-2, B-1, C-4, D-3", 
                                                       "A-4, B-3, C-2, D-1", "A-3, B-4, C-1, D-2"]
                                        elif i % 3 == 1 and include_true_false:
                                            question = f"True or False: {sentences[i]}"
                                            correct = "True" if random.random() > 0.5 else "False"
                                            options = ["True", "False"]
                                        elif i % 3 == 2 and include_descriptive:
                                            question = f"Explain in detail: {sentences[i]}"
                                            correct = "Descriptive answer - to be evaluated manually"
                                            options = ["Descriptive answer - to be evaluated manually"]
                                        else:
                                            question = f"What is the significance of: '{sentences[i]}'?"
                                            correct = f"Answer option {random.randint(1, 4)}"
                                            options = [f"Answer option {j}" for j in range(1, 5)]
                                        
                                        db.add_paper_question(paper_id, question, correct, options)
                            
                            else:  # Exam Mode
                                # Calculate number of questions based on distribution
                                mcq_count = int((num_questions * mcq_percentage) / 100)
                                desc_count = num_questions - mcq_count
                                
                                # Generate MCQs
                                for i in range(min(mcq_count, len(sentences))):
                                    if i < len(sentences):
                                        question = f"MCQ ({total_marks//num_questions} marks): {sentences[i]}?"
                                        correct = f"Answer {random.randint(1, 4)}"
                                        options = [f"Answer {j}" for j in range(1, 5)]
                                        
                                        db.add_paper_question(paper_id, question, correct, options)
                                
                                # Generate descriptive questions
                                for i in range(min(desc_count, len(sentences) - mcq_count)):
                                    if i + mcq_count < len(sentences):
                                        marks = (total_marks // num_questions) * 2  # Descriptive worth more
                                        question = f"Descriptive ({marks} marks): Elaborate on {sentences[i + mcq_count]}"
                                        correct = "Descriptive answer - evaluated manually"
                                        options = ["Descriptive answer - evaluated manually"]
                                        
                                        db.add_paper_question(paper_id, question, correct, options)
                            
                            st.success(f"Question paper generated successfully! Paper ID: {paper_id}")
                            
                            # Show preview button
                            if st.button("Preview Question Paper"):
                                # Get paper details and questions
                                paper = db.get_question_paper(paper_id)
                                questions = db.get_paper_questions(paper_id)
                                
                                st.subheader(f"Question Paper #{paper_id}")
                                st.write(f"Based on: {os.path.basename(paper[4])}")
                                st.write(f"Generated on: {paper[3]}")
                                
                                if mode == "Exam Mode":
                                    st.write(f"Time Limit: {settings['time_limit']} minutes")
                                    st.write(f"Total Marks: {settings['total_marks']}")
                                
                                # Display questions
                                for i, q in enumerate(questions):
                                    q_options = db.get_paper_question_options(q[0])
                                    
                                    st.markdown(f"**Question {i+1}**: {q[2]}")
                                    
                                    for j, opt in enumerate(q_options):
                                        st.markdown(f"- {opt[2]}")
                                    
                                    st.markdown("---")
                            
                        except Exception as e:
                            st.error(f"Error generating question paper: {str(e)}")
            else:
                st.warning("No summary found for the selected document. Please add a summary first.")
        else:
            st.warning("No documents with summaries found. Please upload documents and add summaries first.")
    except Exception as e:
        st.error(f"Error loading documents with summaries: {str(e)}")
        st.info("Make sure you have created documents and added summaries to them.")

# Footer
st.divider()
st.caption("Edumate - Your AI-Powered Education Platform") 