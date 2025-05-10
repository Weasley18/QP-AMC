import streamlit as st
import json
import os
from database import Database
from Qgen import generate_quiz, save_quiz_to_file

st.set_page_config(page_title="QUIZ", layout="centered")

# Custom dark theme CSS
st.markdown("""
    <style>
        body {
            background-color: #001f3f;
            color: white;
        }
        .stApp {
            background-color: #001f3f;
        }
        h1, h2, h3, h4, h5, h6, p, div {
            color: #ffffff !important;
        }
        .stRadio > div {
            background-color: #003366;
            padding: 10px;
            border-radius: 10px;
        }
        .stButton > button {
            background-color: #0055a5;
            color: #ffffff;
        }
        .stExpander {
            background-color: #003366;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize database connection
db = Database("edumate.db")

# Function to load quiz data from file
def load_quiz_data(path="quiz.json"):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return None
    return None

# Page title
st.title("QUIZ")

# Document selection for quiz generation
st.subheader("Generate Quiz from Document")

try:
    # Get documents from database
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
            "Select Document for Quiz", 
            options=list(doc_options.keys()),
            help="Select a document to generate quiz questions from"
        )
        
        selected_doc_id = doc_options[selected_doc]
        
        # Get document details
        document = db.cursor.execute('''
            SELECT document_id, text_content, original_file_url 
            FROM documents
            WHERE document_id = ?
        ''', (selected_doc_id,)).fetchone()
        
        if document and document[1]:  # If document has text content
            # Quiz generation settings
            col1, col2 = st.columns(2)
            with col1:
                num_questions = st.slider("Number of Questions", min_value=3, max_value=15, value=5)
            with col2:
                # Try to extract topics if available
                topics = ""
                text_content = document[1]
                try:
                    if text_content.strip().startswith('{') and text_content.strip().endswith('}'):
                        ocr_data = json.loads(text_content)
                        if 'topics' in ocr_data:
                            if isinstance(ocr_data['topics'], list):
                                topics = ', '.join(ocr_data['topics'])
                            else:
                                topics = str(ocr_data['topics'])
                        if 'subject' in ocr_data:
                            topics = f"{ocr_data['subject']}: {topics}"
                except:
                    pass
                
                topic_input = st.text_input("Topic/Subject", value=topics)
            
            # Generate Quiz button
            if st.button("Generate Quiz"):
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
                        
                        # Direct to quiz interface
                        st.session_state.show_quiz = True
                        st.rerun()
                    else:
                        st.error("Failed to generate quiz. Please try again.")
        else:
            st.warning("Selected document has no text content. Please choose another document.")
    else:
        st.warning("No documents found. Please upload a document first.")
except Exception as e:
    st.error(f"Error loading documents: {str(e)}")

# Quiz Interface
st.markdown("---")
if st.session_state.get('show_quiz', False) or os.path.exists("quiz.json"):
    quiz_data = load_quiz_data()
    
    if quiz_data:
        st.subheader("Take the Quiz")
        st.write("Choose your answers below:")

        # Create a dict to store user responses
        user_responses = {}
        for i, q in enumerate(quiz_data):
            st.subheader(f"Question {i+1}: {q['question']}")
            user_responses[i] = st.radio("Choose your answer:", q["options"], key=f"q_{i}")

        if st.button("Submit Answers"):
            score = 0
            for i, q in enumerate(quiz_data):
                correct = q["answer"]
                chosen = user_responses[i]
                if correct == chosen:
                    score += 1

            st.success(f"🎯 Your Score: {score}/{len(quiz_data)}")

            with st.expander("Review Answers"):
                for i, q in enumerate(quiz_data):
                    correct = q["answer"]
                    chosen = user_responses[i]
                    st.markdown(f"**Q{i+1}:** {q['question']}")
                    st.markdown(f"Your answer: `{chosen}`")
                    st.markdown(f"Correct answer: `{correct}`")
                    st.markdown("---")
    else:
        st.error("⚠️ No quiz data found. Please generate a quiz first.") 