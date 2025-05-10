# Edumate

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version 1.0.0">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.8+-brightgreen.svg" alt="Python 3.8+">
</p>

## 📚 Your AI-Powered Education Platform

Edumate is an intelligent education platform that helps students and teachers work with educational content. 
The platform allows users to upload documents, generate summaries, create quizzes, and generate comprehensive question papers with varying difficulty levels.

## ✨ Features

- **User Management**: Create and manage student and teacher accounts
- **Document Management**: Upload and organize educational materials
- **Summary Generation**: Create and store summaries of educational content
- **Quiz Creation**: Generate interactive quizzes from document content
- **Question Paper Generation**: Create question papers with three different modes:
  - **Basic Mode**: Simple MCQ questions with customizable options
  - **Advanced Mode**: Mix of match-the-following, true/false, and descriptive questions
  - **Exam Mode**: Full exam simulation with time limits and marks distribution
- **Database Integration**: All content is stored in a SQLite database for persistence

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Streamlit
- FastAPI (for API mode)
- SQLite3

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/edumate.git
cd edumate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Streamlit application:
```bash
streamlit run app.py
```

4. Access the application at: http://localhost:8501

## 📱 Usage

1. **Upload Documents**: Use the Documents tab to upload educational content
2. **Create Summaries**: Add summaries to your documents for better understanding
3. **Generate Quizzes**: Create quizzes from your documents to test knowledge
4. **Create Question Papers**: Generate comprehensive question papers with different modes

## 📕 Database Schema

Edumate uses SQLite with the following key tables:
- **users**: Store user information
- **documents**: Store uploaded documents
- **summaries**: Store document summaries
- **quizzes**: Store quiz information
- **question_papers**: Store generated question papers

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Streamlit for the easy-to-use UI framework
- FastAPI for the API integration
- SQLite for simple database integration