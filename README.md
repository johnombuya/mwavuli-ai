# Project Mwavuli - Content Verification API

A FastAPI-based content verification system designed for detecting harmful information in the Kenyan political context. This system combines lexicon-based keyword detection, AI-powered toxicity analysis, and contextual understanding to identify potentially harmful content during election periods.

## Features

- **Lexicon-Based Detection**: Immediate flagging of high-risk Kenyan political keywords (e.g., "madoadoa", "kwekwe")
- **AI Toxicity Analysis**: Multilingual toxicity detection using Detoxify
- **Context-Aware Analysis**: Google Gemini integration for detecting subtle political incitement
- **Multi-Language Support**: Responses in English, Swahili, and Sheng
- **Firebase Integration**: Anonymized logging of reports for pattern analysis
- **WhatsApp Ready**: Designed for integration with n8n/Twilio workflows

## Architecture

```
WhatsApp → n8n/Twilio → FastAPI → MwavuliAnalyzer → Detoxify + Gemini → Firebase
```

## Prerequisites

- Python 3.10+ (tested with Python 3.14)
- Firebase project with Firestore enabled
- Google Gemini API key
- (Optional) Twilio account for WhatsApp integration

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd niru_mwavuli
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: The first time Detoxify runs, it will download the multilingual model (~500MB). This happens automatically on the first API call.

### 4. Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing project
3. Enable **Firestore Database**:
   - Go to Firestore Database
   - Click "Create database"
   - Choose "Start in production mode" (you can add security rules later)
   - Select your preferred region
   - **Important**: If you create a custom database (not default), note the database ID
4. Create a Service Account:
   - Go to **Project Settings** → **Service Accounts**
   - Click **Generate new private key**
   - Download the JSON file
   - Save it as `firebase-service-account.json` in the project root

### 5. Configure Environment Variables

1. Copy the environment template:
   ```bash
   # Windows PowerShell
   Copy-Item env.template .env
   
   # Linux/Mac
   cp env.template .env
   ```

2. Edit `.env` and fill in your values:
   ```env
   # Firebase Configuration
   FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
   FIREBASE_DATABASE_ID=mwavuli-nira-db  # Leave empty for default database
   
   # Google Gemini API Key
   # Get from: https://makersuite.google.com/app/apikey
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Twilio Configuration (optional, for WhatsApp integration)
   TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
   ```

### 6. Clear Detoxify Cache (if needed)

If you encounter model loading errors, clear the corrupted cache:

```bash
# Windows PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\torch\hub\*" -ErrorAction SilentlyContinue

# Linux/Mac
rm -rf ~/.cache/torch/hub/*
```

## Running the Application

### Development Mode (with auto-reload)

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using Docker (Optional)

```bash
docker build -t mwavuli-api .
docker run -p 8000:8000 --env-file .env mwavuli-api
```

## API Endpoints

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "version": "1.0.0",
  "model_loaded": true
}
```

### Verify Text

```bash
POST /api/v1/verify/text
Content-Type: application/json

{
  "text": "Your text to analyze",
  "sender_id": "unique_sender_id",
  "county": "Nairobi"  // Optional
}
```

**Response:**
```json
{
  "risk_level": "HIGH",
  "messages": {
    "english": "Warning: This message contains harmful content...",
    "swahili": "Onyo: Ujumbe huu una maudhui hatari...",
    "sheng": "Heads up: Message iko na vitu mbaya..."
  },
  "report_id": "abc123",
  "prebunking_tip": "For official election results, always visit iebc.or.ke",
  "scores": {
    "toxicity": 0.85,
    "severe_toxicity": 0.12
  },
  "matched_keyword": "madoadoa"
}
```

### Verify Media (Placeholder)

```bash
POST /api/v1/verify/media
Content-Type: application/json

{
  "media_url": "https://example.com/video.mp4",
  "media_type": "video",
  "sender_id": "unique_sender_id",
  "county": "Nairobi"  // Optional
}
```

## Testing

### Using the Test Script

```bash
# Windows (Git Bash)
bash test_api.sh

# Linux/Mac
chmod +x test_api.sh
./test_api.sh
```

### Manual Testing with cURL

```bash
# Test safe text
curl -X POST http://localhost:8000/api/v1/verify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "sender_id": "test123"}'

# Test high-risk text
curl -X POST http://localhost:8000/api/v1/verify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Those madoadoa must leave", "sender_id": "test456", "county": "Nairobi"}'
```

### Using the Interactive API Docs

Visit `http://localhost:8000/docs` for Swagger UI documentation with interactive testing.

## Integration with n8n

### Expected Request Format

```json
{
  "text": "Message content from WhatsApp",
  "sender_id": "whatsapp:+254712345678",
  "county": "Nairobi"
}
```

### Expected Response Format

```json
{
  "risk_level": "HIGH|MEDIUM|LOW",
  "messages": {
    "english": "...",
    "swahili": "...",
    "sheng": "..."
  },
  "report_id": "firestore_document_id",
  "prebunking_tip": "For official election results, always visit iebc.or.ke"
}
```

### n8n Workflow Example

1. **HTTP Request Node** → POST to `/api/v1/verify/text`
2. **IF Node** → Check `risk_level === "HIGH"`
3. **Twilio Node** → Send WhatsApp message using `messages.swahili` or `messages.sheng`
4. **Always include** `prebunking_tip` in responses

## Project Structure

```
niru_mwavuli/
├── main.py                      # FastAPI application
├── models/
│   └── text_analyzer.py         # MwavuliAnalyzer class
├── utils/
│   ├── db.py                    # Firebase Firestore utility
│   └── lexicon.py               # Kenya-specific keywords
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── env.template                 # Environment template
├── firebase-service-account.example.json  # Firebase template
├── test_api.sh                  # Test script
└── README.md                    # This file
```

## Risk Levels

- **HIGH**: Contains high-risk keywords or toxicity score > 0.7
- **MEDIUM**: Toxicity score between 0.4-0.7
- **LOW**: Toxicity score < 0.4

## Troubleshooting

### Detoxify Model Loading Error

**Error**: `RuntimeError: PytorchStreamReader failed reading zip archive`

**Solution**: Clear the corrupted cache (see Installation step 6)

### Firebase Database Error

**Error**: `404 The database (default) does not exist`

**Solution**: 
1. Ensure Firestore is enabled in Firebase Console
2. If using a custom database, set `FIREBASE_DATABASE_ID` in `.env`
3. Visit the URL provided in the error to create the database

### Gemini API Error

**Error**: `Warning: Failed to initialize Gemini`

**Solution**:
1. Verify `GEMINI_API_KEY` is set correctly in `.env`
2. Check API key is valid at [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Ensure you have quota available

### Port Already in Use

**Error**: `Address already in use`

**Solution**: Use a different port:
```bash
uvicorn main:app --port 8001
```

## Security Notes

- **Never commit** `.env` or `firebase-service-account.json` to git
- Rotate Firebase credentials if accidentally exposed
- Keep API keys secure and rotate regularly
- Use environment variables for all sensitive data in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Contact the development team

## Acknowledgments

- Detoxify for toxicity detection
- Google Gemini for translation and context analysis
- Firebase for data storage
- FastAPI for the web framework

