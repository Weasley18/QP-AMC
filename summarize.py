import os
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
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please add it to your .env file.")
        
    client = genai.Client(
        api_key=api_key,
    )

    model = "gemini-2.5-flash-preview-04-17"
    
    # Prepare the prompt with context
    context = ""
    if subject:
        context += f"Subject: {subject}\n"
    if topics:
        context += f"Topics: {topics}\n"
    
    prompt = f"""{context}
    Please create a comprehensive summary of the following text. Include the main ideas, 
    key points, and important concepts. Structure the summary to be clear and concise.
    
    TEXT TO SUMMARIZE:
    {text}
    """

    # Set up the generation config
    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,  # Low temperature for factual summaries
        max_output_tokens=2048,
        response_mime_type="application/json"
    )

    # Create the content parts
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    # Add system instructions
    system_instruction = """You are a professional educational content summarizer.
    Create an informative summary that captures the essence of the text.
    Return your summary as a JSON object with the following structure:
    {
        "summary": "The comprehensive summary text",
        "key_points": ["List of key points"],
        "concepts": ["List of important concepts or terms"]
    }
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            generation_config=generate_content_config,
            system_instruction=types.Part.from_text(text=system_instruction),
        )
        
        # Parse the JSON response
        try:
            summary_data = response.json()
            return summary_data
        except Exception as e:
            print(f"Error parsing JSON response: {e}")
            # If JSON parsing fails, return the raw text
            return {
                "summary": response.text,
                "key_points": [],
                "concepts": []
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