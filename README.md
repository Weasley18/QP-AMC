# LearnLM Chatbot

A simple interactive chatbot powered by Google's LearnLM model, designed to function as a friendly, supportive tutor.

## Prerequisites

- Python 3.7 or higher
- Google Genai Python library
- Python-dotenv library

## Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root directory with your API key:

```
GEMINI_API_KEY=AIzaSyD0Rxdt-R2nSEGcDsoYvvEUKOOdb5K69H0
```

## Usage

Run the chatbot with:

```bash
python learnlm_chatbot.py
```

- Type your messages and press Enter to send
- The chatbot will remember the conversation history
- Type 'exit' to end the conversation

## Features

- Interactive conversation with LearnLM's tutor model
- Maintains conversation history
- Supports multiple languages (English, Kannada, Hinglish, Hindi)
- Real-time streaming of responses