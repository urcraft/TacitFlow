# TacitFlow

A conversational BPMN diagram generator powered by Google Gemini AI. Simply describe your business process in natural language, and TacitFlow will automatically create professional BPMN diagrams for you.

## Features

- 🤖 **AI-Powered Generation**: Describe processes in plain English and get instant BPMN diagrams
- 🖼️ **Interactive Editor**: Visual BPMN diagram editor with real-time updates
- 💬 **Conversational Interface**: Iteratively refine and modify your diagrams through chat
- 📊 **Process Analysis**: Get suggestions for AS-IS to TO-BE process improvements

## Quick Start

1. **Install dependencies**:
   ```bash
   # Using uv (recommended):
   uv sync
   
   # Or using pip:
   pip install google-genai gradio
   ```

2. **Set up Google Gemini API**:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser** to the displayed URL (typically `http://localhost:7860`)

## Usage

1. Describe your business process in the chat interface
2. Watch as TacitFlow generates a BPMN diagram automatically
3. Ask for modifications, analysis, or improvements
4. Export or refine your diagram as needed

## Technology Stack

- **Frontend**: Gradio web interface with bpmn-js editor
- **AI**: Google Gemini for natural language processing
- **Backend**: Python with BPMN 2.0 XML generation

## Requirements

- Python 3.9+
- Google Gemini API key
- Dependencies listed in `pyproject.toml`