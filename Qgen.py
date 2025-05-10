# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_quiz(text, topic=None, num_questions=5):
    """
    Generate a quiz from text content using Google Gemini API.
    
    Args:
        text (str): The text content to create quiz questions from
        topic (str, optional): The topic of the content
        num_questions (int): Number of questions to generate
        
    Returns:
        list: A list of quiz questions in the format:
             [{"question": "...", "options": ["...", "..."], "answer": "..."}]
    """
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-04-17"
    
    # Prepare the prompt with context
    context = ""
    if topic:
        context += f"Topic: {topic}\n"
    
    prompt = f"""{context}
    Please create a quiz with {num_questions} multiple-choice questions based on the following text.
    
    TEXT TO CREATE QUIZ FROM:
    {text}
    """
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""You are a question paper setter.
You will be given notes and topics.
You need to make a practice quiz for the user.
The output will be a JSON array containing quiz questions.
Each question should have 3 fields: 
- "question": the text of the question
- "options": an array of possible answers (provide 4 options)
- "answer": the correct answer (must be exactly one of the options)

Example format:
[
  {
    "question": "What is the capital of France?",
    "options": ["London", "Paris", "Berlin", "Madrid"],
    "answer": "Paris"
  },
  {
    "question": "Who wrote Romeo and Juliet?",
    "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
    "answer": "William Shakespeare"
  }
]"""),
        ],
    )

    try:
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text
            
        # Try to parse the JSON response
        try:
            quiz_data = json.loads(response_text)
            return quiz_data
        except json.JSONDecodeError:
            # If JSON parsing fails, return an error message
            print(f"Error parsing JSON response. Raw text: {response_text[:200]}...")
            return None
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def save_quiz_to_file(quiz_data, output_path="quiz.json"):
    """Save quiz data to a JSON file"""
    with open(output_path, "w") as f:
        json.dump(quiz_data, f, indent=2)
    print(f"Quiz saved to {output_path}")

if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    Machine learning is a subset of artificial intelligence that involves training algorithms to learn patterns 
    from data without being explicitly programmed. The process typically involves collecting data, preprocessing it, 
    selecting a model, training the model on the data, evaluating its performance, and then deploying it for predictions. 
    Common machine learning algorithms include linear regression, logistic regression, decision trees, random forests, 
    support vector machines, k-nearest neighbors, and neural networks. Each algorithm has its strengths and weaknesses, 
    making them suitable for different types of problems. The field has seen remarkable growth in recent years due to 
    increased computational power, larger datasets, and advancements in algorithm design.
    """
    
    topic = "Machine Learning"
    
    quiz = generate_quiz(sample_text, topic)
    if quiz:
        save_quiz_to_file(quiz)
        print(f"Generated {len(quiz)} quiz questions.")