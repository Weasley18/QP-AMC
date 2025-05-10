import streamlit as st
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
import requests
import urllib.parse
import json

# Load environment variables
load_dotenv()

# Get API keys
gemini_api_key = os.environ.get("GEMINI_API_KEY")
youtube_api_key = os.environ.get("YOUTUBE_API_KEY")

# Configure the Gemini API
genai.configure(api_key=gemini_api_key)

def search_youtube_videos(query, language, max_results=3):
    """Search for YouTube videos using direct API call or fallback to a simple search."""
    videos = []
    
    # First try the API if key is available
    if youtube_api_key:
        try:
            videos = api_search_youtube(query, language, max_results)
        except Exception as e:
            st.error(f"YouTube API error: {str(e)}")
            # If API fails, fall back to the fallback method
            videos = fallback_search_youtube(query, language, max_results)
    else:
        # No API key, use fallback method
        st.warning("YouTube API key not found. Using basic search instead.")
        videos = fallback_search_youtube(query, language, max_results)
    
    return videos

def api_search_youtube(query, language, max_results=3):
    """Search YouTube using the official API."""
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
        st.error(f"YouTube API error: Status code {response.status_code}")
        if "error" in response.json():
            st.error(f"API error message: {response.json()['error'].get('message', 'Unknown error')}")
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

def fallback_search_youtube(query, language, max_results=3):
    """A fallback method to get YouTube results without the API (creates direct search URLs)."""
    # Format the search query
    if language.lower() != "english":
        query = f"{query} {language}"
    
    # URL encode the query
    encoded_query = urllib.parse.quote(query)
    
    # Create a direct search URL
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
    
    # Generate generic search results
    videos = []
    videos.append({
        "title": f"YouTube search results for: {query}",
        "url": search_url
    })
    
    # Add some specific search variations if needed
    if len(query.split()) > 1:
        # Add a more specific search with quotes
        specific_query = f'"{query}"'
        encoded_specific = urllib.parse.quote(specific_query)
        videos.append({
            "title": f"Exact match search for: {query}",
            "url": f"https://www.youtube.com/results?search_query={encoded_specific}"
        })
    
    # Add a "how to" variation
    how_to_query = f"how to {query}"
    encoded_how_to = urllib.parse.quote(how_to_query)
    videos.append({
        "title": f"How to tutorials about: {query}",
        "url": f"https://www.youtube.com/results?search_query={encoded_how_to}"
    })
    
    return videos[:max_results]

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

def initialize_chat_model():
    """Initialize the LearnLM chat model"""
    generation_config = genai.GenerationConfig(
        temperature=0.7,
        response_mime_type="text/plain",
    )
    
    model = genai.GenerativeModel(
        model_name="learnlm-2.0-flash-experimental",
        generation_config=generation_config
    )
    
    return model

def create_chatbot_ui():
    """Create a Streamlit UI for the LearnLM chatbot"""
    st.title("Learning Assistant Chatbot")
    
    # Custom styles for chat bubbles
    st.markdown("""
    <style>
    .user-message {
        background-color: #004578;
        color: white;
        padding: 10px;
        border-radius: 15px 15px 0px 15px;
        margin: 10px 0;
    }
    .bot-message {
        background-color: #2b5797;
        color: white;
        padding: 10px;
        border-radius: 15px 15px 15px 0px;
        margin: 10px 0;
    }
    .youtube-container {
        background-color: #333333;
        border-radius: 10px;
        padding: 10px;
        margin-top: 20px;
    }
    .youtube-title {
        color: #ff5555;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state for chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "preferred_language" not in st.session_state:
        st.session_state.preferred_language = "English"
        
    if "language_selected" not in st.session_state:
        st.session_state.language_selected = False
        
    if "chat" not in st.session_state:
        # Initialize the model and chat
        model = initialize_chat_model()
        
        # System instruction for the tutor behavior
        system_prompt = """Be a friendly, supportive tutor. Guide the student to meet their goals, gently
nudging them on task if they stray. Ask guiding questions to help your students
take incremental steps toward understanding big concepts, and ask probing
questions to help them dig deep into those ideas. Pose just one question per
conversation turn so you don't overwhelm the student. Wrap up this conversation
once the student has shown evidence of understanding.

Before starting ask the user their preferred language. (English, Kannada, Hinglish or Hindi)"""

        # Initialize the chat session
        st.session_state.chat = model.start_chat()
        
        # Send a system message to set up the behavior
        initial_response = st.session_state.chat.send_message(system_prompt)
        
        # Add the initial message to the chat history
        st.session_state.messages.append({"role": "assistant", "content": initial_response.text})
    
    # Display language selector if not already selected
    if not st.session_state.language_selected:
        st.info("The chatbot will ask you to select a language. Choose from English, Hindi, Kannada, or Hinglish.")

    # Create a container for chat messages
    chat_container = st.container()
    
    # Display chat messages in the container
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">You: {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-message">Assistant: {message["content"]}</div>', unsafe_allow_html=True)

    # Create a form for user input to prevent auto-reloading
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your message here:", key="user_input")
        submit_button = st.form_submit_button("Send")
    
    # Handle user input when form is submitted
    if submit_button and user_input:
        # Handle exit command
        if user_input.lower() == "exit":
            # Add exit message to history
            st.session_state.messages.append({"role": "user", "content": "exit"})
            
            # Add a farewell message
            st.session_state.messages.append({"role": "assistant", "content": "Goodbye! I hope our conversation was helpful. Before you go, here are some resources related to our discussion:"})
            
            # Extract topic from previous conversation and show resources
            all_user_text = " ".join([msg["content"] for msg in st.session_state.messages if msg["role"] == "user"])
            topic = get_main_topic(all_user_text)
            
            if topic:
                # Store topic and trigger YouTube search
                st.session_state.exit_topic = topic
                st.session_state.show_exit_resources = True
                
                # Use rerun to update the display
                st.rerun()
        else:
            # Process normal user input
            # Check for language selection
            lower_input = user_input.lower()
            if not st.session_state.language_selected and any(lang in lower_input for lang in ["english", "hindi", "kannada", "hinglish"]):
                # Set preferred language
                if "english" in lower_input:
                    st.session_state.preferred_language = "English"
                elif "hindi" in lower_input:
                    st.session_state.preferred_language = "Hindi"
                elif "kannada" in lower_input:
                    st.session_state.preferred_language = "Kannada"
                elif "hinglish" in lower_input:
                    st.session_state.preferred_language = "Hinglish"
                    
                st.session_state.language_selected = True
            
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get response from model
            with st.spinner("Thinking..."):
                response = st.session_state.chat.send_message(user_input)
                
            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            # Use st.rerun() to update the chat history display without interrupting the chat flow
            st.rerun()
    
    # Check if we should display exit resources
    if "show_exit_resources" in st.session_state and st.session_state.show_exit_resources:
        # Get the topic from session state
        topic = st.session_state.exit_topic
        
        # Display YouTube recommendations
        st.markdown(f'<h3>YouTube videos about "{topic}" in {st.session_state.preferred_language}:</h3>', unsafe_allow_html=True)
        
        with st.spinner("Finding resources..."):
            videos = search_youtube_videos(topic, st.session_state.preferred_language)
        
        if videos:
            for i, video in enumerate(videos, 1):
                st.markdown(f"""
                <div class="youtube-container">
                    <p class="youtube-title">{i}. {video['title']}</p>
                    <a href="{video['url']}" target="_blank">{video['url']}</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No relevant videos found.")
        
        # Add a reset chat button
        if st.button("Start New Chat"):
            # Reset the chat session
            for key in ['messages', 'chat', 'show_exit_resources', 'exit_topic']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    # Display YouTube recommendations button if there's at least one user message and not in exit mode
    elif len([msg for msg in st.session_state.messages if msg["role"] == "user"]) >= 1 and not st.session_state.get('show_exit_resources', False):
        if st.button("Get Learning Resources"):
            # Extract the main topic from all user messages
            all_user_text = " ".join([msg["content"] for msg in st.session_state.messages if msg["role"] == "user"])
            topic = get_main_topic(all_user_text)
            
            if topic:
                # Store topic for display
                st.session_state.resource_topic = topic
                st.session_state.show_resources = True
                st.rerun()
            else:
                st.info("Could not identify a specific topic from your conversation. Try discussing a specific subject.")
    
    # Check if we should display resources (from button click)
    if "show_resources" in st.session_state and st.session_state.show_resources and "resource_topic" in st.session_state:
        topic = st.session_state.resource_topic
        st.markdown(f'<h3>YouTube videos about "{topic}" in {st.session_state.preferred_language}:</h3>', unsafe_allow_html=True)
        
        with st.spinner("Searching YouTube..."):
            videos = search_youtube_videos(topic, st.session_state.preferred_language)
        
        if videos:
            for i, video in enumerate(videos, 1):
                st.markdown(f"""
                <div class="youtube-container">
                    <p class="youtube-title">{i}. {video['title']}</p>
                    <a href="{video['url']}" target="_blank">{video['url']}</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No relevant videos found. Try a different topic.")
            
        # Add a close button for resources
        if st.button("Close Resources"):
            del st.session_state['show_resources']
            del st.session_state['resource_topic']
            st.rerun()

if __name__ == "__main__":
    create_chatbot_ui() 