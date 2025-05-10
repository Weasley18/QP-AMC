import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
import googleapiclient.discovery
import googleapiclient.errors
import requests
import urllib.parse
import json

# Load environment variables from .env file
load_dotenv()

# Get the API keys from environment variables
gemini_api_key = os.environ.get("GEMINI_API_KEY")
youtube_api_key = os.environ.get("YOUTUBE_API_KEY")

if not gemini_api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file with GEMINI_API_KEY=your_api_key_here")
    exit(1)

if not youtube_api_key:
    print("Warning: YOUTUBE_API_KEY not found in environment variables.")
    print("YouTube recommendations will not be available.")

# Configure the Google Generative AI library
genai.configure(api_key=gemini_api_key)

def search_youtube_videos(query, language, max_results=3):
    """Search for YouTube videos using direct API call."""
    if not youtube_api_key:
        return []
    
    try:
        # Adjust language parameter for YouTube search
        lang_param = {
            "english": "en",
            "hindi": "hi",
            "kannada": "kn",
            "hinglish": "hi"  # Default to Hindi for Hinglish
        }.get(language.lower(), "en")
        
        # Add language to query for better results
        if language.lower() != "english":
            query = f"{query} {language}"
        
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        
        # Build the API URL
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={encoded_query}&type=video&relevanceLanguage={lang_param}&key={youtube_api_key}"
        
        # Make the request
        response = requests.get(url, timeout=10)
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"YouTube API error: Status code {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
            return []
        
        # Parse the response
        data = response.json()
        
        videos = []
        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            videos.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })
        
        return videos
    except requests.exceptions.RequestException as e:
        print(f"YouTube API request error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"YouTube API response parsing error: {e}")
        return []
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []



def get_main_topic(text):
    """Extract the main topic from a single text message."""
    # Remove common words that might not be topics
    common_words = ["the", "a", "an", "is", "are", "was", "were", "do", "does", 
                    "did", "have", "has", "had", "can", "could", "will", "would", 
                    "should", "may", "might", "must", "and", "or", "but", "if", 
                    "then", "else", "when", "where", "why", "how", "what", "who"]
    
    # Split into words and filter
    words = re.findall(r'\b\w+\b', text.lower())
    potential_topics = [word for word in words if len(word) > 3 and word not in common_words]
    
    # Count occurrences
    word_counts = {}
    for word in potential_topics:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Sort by count and return top topic
    sorted_topics = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_topics:
        return sorted_topics[0][0]  # Return the most frequent non-common word
    return None

def create_chatbot():
    # Create a model instance
    generation_config = genai.GenerationConfig(
        temperature=0.7,
        response_mime_type="text/plain",
    )
    
    model = genai.GenerativeModel(
        model_name="learnlm-2.0-flash-experimental",
        generation_config=generation_config
    )
    
    # System instruction for the tutor behavior
    system_prompt = """Be a friendly, supportive tutor. Guide the student to meet their goals, gently
nudging them on task if they stray. Ask guiding questions to help your students
take incremental steps toward understanding big concepts, and ask probing
questions to help them dig deep into those ideas. Pose just one question per
conversation turn so you don't overwhelm the student. Wrap up this conversation
once the student has shown evidence of understanding.

Before starting ask the user their preferred language. (English, Kannada, Hinglish or Hindi)"""
    
    # Initialize the chat session
    chat = model.start_chat()
    
    # Send a system message to set up the behavior
    initial_response = chat.send_message(system_prompt)
    
    # Track user's preferred language
    preferred_language = "English"  # Default
    language_detected = False
    
    # Track the last user message for topic extraction
    last_user_message = ""
    
    print("LearnLM Chatbot")
    print("Type 'exit' to end the conversation")
    print("-" * 50)
    
    # Print the initial greeting from the model
    print(f"\nChatbot: {initial_response.text}")
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Store the last user message for topic extraction
        if user_input.lower() != 'exit':
            last_user_message = user_input
        
        if user_input.lower() == 'exit':
            # Get the main topic from the last user message
            topic = get_main_topic(last_user_message)
            
            print("\nChatbot: Goodbye! Have a great day!")
            
            # If a topic was detected, offer YouTube recommendations
            if topic:
                print(f"\nBefore you go, here are some YouTube videos about '{topic}' in {preferred_language}:")
                print(f"Searching YouTube... (this may take a few seconds)")
                videos = search_youtube_videos(topic, preferred_language)
                
                if videos:
                    for i, video in enumerate(videos, 1):
                        print(f"{i}. {video['title']}")
                        print(f"   {video['url']}")
                else:
                    print("Sorry, I couldn't find any relevant videos at the moment.")
            
            break
        
        # Send message and get response
        print("\nChatbot: ", end="")
        
        response = chat.send_message(user_input, stream=True)
        
        response_text = ""
        for chunk in response:
            if hasattr(chunk, "text"):
                print(chunk.text, end="")
                response_text += chunk.text
        
        # Check for language detection in the first few exchanges
        if not language_detected and len(last_user_message) == 0:
            lower_response = response_text.lower()
            if "language" in lower_response or "भाषा" in lower_response:
                language_detected = True
        # Detect language preference from user's second message
        elif language_detected and len(last_user_message) > 0 and not preferred_language.lower() in ["hindi", "kannada", "hinglish"]:
            lower_input = user_input.lower()
            if "english" in lower_input:
                preferred_language = "English"
            elif "hindi" in lower_input:
                preferred_language = "Hindi"
            elif "kannada" in lower_input:
                preferred_language = "Kannada"
            elif "hinglish" in lower_input:
                preferred_language = "Hinglish"

if __name__ == "__main__":
    create_chatbot() 