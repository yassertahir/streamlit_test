# VC Assistant

A Streamlit application that evaluates startup proposals like a venture capitalist using OpenAI's Assistants API. Upload your business proposal documents and get professional feedback, scoring, and recommendations.

## Features

- 💬 Interactive chat interface to discuss your startup ideas
- 📄 Upload and analyze multiple document formats (PDF, CSV, XLSX, DOCX, TXT)
- 🔍 Team evaluation with CV analysis
- 📊 Market and competitor analysis
- 💯 Comprehensive scoring on a 1-10 scale
- 📝 Structured feedback including strengths and areas for improvement

## Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd streamlit_test
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Configure OpenAI API key:
   - Create a `.streamlit/secrets.toml` file with your API key:
   ```toml
   openai_api_key = "your-openai-api-key"
   ```

## Usage

1. Run the Streamlit application:

```bash
streamlit run app.py
```

2. Open your browser at `http://localhost:8501`

3. Interact with the VC Assistant:
   - Type your startup proposal in the chat input
   - Upload relevant documents (business plans, team CVs, market data)
   - Get comprehensive feedback and evaluation

## How It Works

1. **Assistant Creation**: The app creates a specialized OpenAI Assistant with VC expertise
2. **Document Processing**: Uploaded files are processed with appropriate tools (file_search for documents, code_interpreter for data files)
3. **Analysis & Evaluation**: The assistant analyzes your proposal and documents
4. **Structured Response**: The assistant provides detailed feedback and recommendations

## Project Structure

- `app.py`: Main Streamlit application
- `utils.py`: Utility functions for OpenAI Assistant creation and management
- `requirements.txt`: Python dependencies
- `.streamlit/secrets.toml`: Configuration secrets (API keys)

## Requirements

- Python 3.7+
- OpenAI API key with access to Assistants API
- Internet connection