# LearnLM Chatbot

A simple interactive chatbot powered by Google's LearnLM model, designed to function as a friendly, supportive tutor.

## Prerequisites

- Python 3.7 or higher
- Google Genai Python library
- Python-dotenv library
- Google API Python Client

## Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root directory with your API keys:


## Usage

Run the chatbot with:

```bash
python learnlm_chatbot.py
```

- Type your messages and press Enter to send
- The chatbot will remember the conversation history
- When you type 'exit', the chatbot will show YouTube video recommendations based on your conversation in your preferred language
- Type 'exit' to end the conversation

## Features

- Interactive conversation with LearnLM's tutor model
- Maintains conversation history
- Supports multiple languages (English, Kannada, Hinglish, Hindi)
- Real-time streaming of responses
- YouTube video recommendations on exit based on conversation topics