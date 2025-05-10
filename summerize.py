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

def generate_summary(text, subject=None, topics=None):
    """
    Generate a summary from text content using Google Gemini API.
    
    Args:
        text (str): The text content to summarize
        subject (str, optional): The subject of the document
        topics (str, optional): The topics covered in the document
        
    Returns:
        dict: A dictionary containing the summary
    """
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-04-17"
    
    # Prepare the prompt with context
    context = ""
    if subject:
        context += f"Subject: {subject}\n"
    if topics:
        context += f"Topics: {topics}\n"
    
    prompt = f"""{context}
    Please create a comprehensive summary of the following text. Include topic names and detailed explanations.
    
    TEXT TO SUMMARIZE:
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
            types.Part.from_text(text="""You are an expert teacher and professor.
You are given text and topics from notes, summarize them such that you are teaching it. 
The output should be a json file containing topic names and summary."""),
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
            summary_data = json.loads(response_text)
            return summary_data
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            print(f"Error parsing JSON response. Raw text: {response_text[:200]}...")
            return {
                "summary": response_text,
                "topics": []
            }
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

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
    
    subject = "Computer Science"
    topics = "Artificial Intelligence, Machine Learning"
    
    summary = generate_summary(sample_text, subject, topics)
    print(summary)
