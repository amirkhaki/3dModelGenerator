# 3D Model Generator

A Flask-based web application that generates 3D models from text prompts. The system creates two images from a text description using OpenAI's DALL-E 3 and Stability AI, removes backgrounds, allows users to select one, and then converts it to a 3D model using Meshy.ai.

## Features

- **Multi-language Support**: Automatically translates non-English prompts to English using GPT-4o-mini
- **Dual Image Generation**: Creates images using both DALL-E 3 and Stability AI for variety
- **Background Removal**: Automatically removes backgrounds using remove.bg API
- **3D Model Generation**: Converts selected image to 3D model using Meshy.ai
- **Interactive 3D Viewer**: View and interact with generated 3D models in the browser
- **STL Export**: Download models in STL format for 3D printing

## Technology Stack

- **Backend**: Python 3 with Flask
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **3D Rendering**: Three.js
- **APIs**:
  - OpenAI (DALL-E 3 & GPT-4o-mini)
  - Stability AI (Stable Diffusion XL)
  - remove.bg (Background Removal)
  - Meshy.ai (3D Model Generation)

## Setup Instructions

### 1. Install Dependencies

#### Option A: Using Nix Flakes (Recommended)

If you have Nix with flakes enabled:

```bash
# Enter development shell
nix develop

# Or with direnv (automatic)
direnv allow
```

The flake provides:
- Python 3.11 with all required packages (Flask, openai, requests, python-dotenv)
- Development tools (git, curl)
- Optional: black, flake8 for code quality

#### Option B: Using pip

```bash
pip install -r requirements.txt
```

Required packages:
- Flask==3.0.0
- openai==1.12.0
- requests==2.31.0
- python-dotenv==1.0.0

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your actual API keys:

```env
OPENAI_API_KEY=your-openai-api-key-here
STABILITY_API_KEY=your-stability-api-key-here
REMOVEBG_API_KEY=your-removebg-api-key-here
MESHY_API_KEY=your-meshy-api-key-here
FLASK_SECRET_KEY=your-secret-key-here
```

### 3. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
3dModelGenerator/
├── app.py                 # Main Flask application
├── templates/             # Jinja2 templates
│   ├── index.html        # Prompt input page
│   ├── selection.html    # Image selection page
│   └── viewer.html       # 3D model viewer page
├── index.html            # Original HTML (for reference)
├── selection.html        # Original HTML (for reference)
├── viewer.html           # Original HTML (for reference)
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your API keys (not committed to git)
├── PROMPT.md            # Project specification
└── README.md            # This file
```

## How It Works

1. **Prompt Input** (`/`)
   - User enters a text description in any language
   - If non-English, the text is translated to English using GPT-4o-mini
   - Prompt is enhanced with additional details for better results

2. **Image Generation** (`/generate-images`)
   - Two images are generated simultaneously:
     - Image 1: OpenAI DALL-E 3
     - Image 2: Stability AI (stable-diffusion-xl-1024-v1-0)
   - Backgrounds are removed using remove.bg API
   - Images are stored in session

3. **Image Selection** (`/selection`)
   - User views both generated images
   - Selects one for 3D model generation
   - Selected image is sent for processing

4. **3D Model Generation** (`/viewer`)
   - Selected image is converted to 3D model using Meshy.ai
   - Model status is checked periodically
   - Once ready, 3D model is displayed using Three.js
   - User can interact with the model (rotate, zoom)
   - Download button provides STL format for 3D printing

## API Endpoints

- `GET /` - Main page for prompt input
- `POST /generate-images` - Generate images from prompt
- `GET /selection` - Image selection page
- `POST /select-image` - Process selected image
- `GET /viewer` - 3D model viewer
- `GET /model-status/<task_id>` - Check model generation status
- `GET /download-stl/<task_id>` - Download model in STL format

## Notes

- The application uses session storage for temporary data
- API calls may take some time depending on the service
- Ensure you have sufficient API credits for all services
- The original HTML files are preserved for reference

## Development

To run in development mode with debug enabled:

```bash
python app.py
```

The Flask app runs with `debug=True` by default for development.

## License

MIT License

