import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file with GEMINI_API_KEY=your_api_key_here")
    exit(1)

def create_chatbot():
    client = genai.Client(
        api_key=api_key,
    )
    
    model = "learnlm-2.0-flash-experimental"
    
    # System instruction for the tutor behavior
    system_instruction = """Be a friendly, supportive tutor. Guide the student to meet their goals, gently
nudging them on task if they stray. Ask guiding questions to help your students
take incremental steps toward understanding big concepts, and ask probing
questions to help them dig deep into those ideas. Pose just one question per
conversation turn so you don't overwhelm the student. Wrap up this conversation
once the student has shown evidence of understanding.

Before starting ask the user their preferred language. (English, Kannada, Hinglish or Hindi)"""
    
    # Initialize conversation history
    conversation_history = []
    
    print("LearnLM Chatbot")
    print("Type 'exit' to end the conversation")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        if user_input.lower() == 'exit':
            print("Chatbot: Goodbye! Have a great day!")
            break
        
        # Add user message to history
        conversation_history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_input)],
            )
        )
        
        # Generate response
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=system_instruction),
            ],
        )
        
        print("\nChatbot: ", end="")
        
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=conversation_history,
            config=generate_content_config,
        ):
            # Check if chunk.text is not None before using it
            if chunk.text is not None:
                print(chunk.text, end="")
                response_text += chunk.text
        
        # Add assistant response to history
        conversation_history.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)],
            )
        )

if __name__ == "__main__":
    create_chatbot() 