#!/bin/bash
# Project Mwavuli - API Test Script
# Run this script to test the verification endpoints
#
# Prerequisites:
# 1. Start the server: uvicorn main:app --reload
# 2. Make this script executable: chmod +x test_api.sh
# 3. Run: ./test_api.sh

BASE_URL="http://localhost:8000"

echo "========================================"
echo "Project Mwavuli - API Tests"
echo "========================================"
echo ""

# Test 1: Health Check
echo "1. Testing Health Endpoint..."
echo "   GET /health"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/health" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/health"
echo ""
echo ""

# Test 2: Safe Text (should return LOW risk)
echo "2. Testing Safe Text..."
echo "   POST /api/v1/verify/text"
echo "   Text: 'Hello, how are you today?'"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you today?",
    "sender_id": "test_user_123",
    "county": "Nairobi"
  }' | python -m json.tool 2>/dev/null || curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you today?", "sender_id": "test_user_123", "county": "Nairobi"}'
echo ""
echo ""

# Test 3: Medium Risk Text (general toxic content)
echo "3. Testing Medium Risk Text..."
echo "   POST /api/v1/verify/text"
echo "   Text: 'Those idiots don't know what they are doing'"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Those idiots do not know what they are doing",
    "sender_id": "test_user_456",
    "county": "Mombasa"
  }' | python -m json.tool 2>/dev/null || curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Those idiots do not know what they are doing", "sender_id": "test_user_456", "county": "Mombasa"}'
echo ""
echo ""

# Test 4: HIGH Risk - Lexicon Match (Kenyan political term)
echo "4. Testing HIGH Risk - Kenyan Lexicon Match..."
echo "   POST /api/v1/verify/text"
echo "   Text: 'Those madoadoa must leave our land'"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Those madoadoa must leave our land",
    "sender_id": "test_user_789",
    "county": "Nakuru"
  }' | python -m json.tool 2>/dev/null || curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Those madoadoa must leave our land", "sender_id": "test_user_789", "county": "Nakuru"}'
echo ""
echo ""

# Test 5: HIGH Risk - Another Lexicon Match
echo "5. Testing HIGH Risk - Violence Incitement..."
echo "   POST /api/v1/verify/text"
echo "   Text: 'We must toeni these people from our area'"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We must toeni these people from our area",
    "sender_id": "test_user_abc",
    "county": "Kisumu"
  }' | python -m json.tool 2>/dev/null || curl -s -X POST "${BASE_URL}/api/v1/verify/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "We must toeni these people from our area", "sender_id": "test_user_abc", "county": "Kisumu"}'
echo ""
echo ""

# Test 6: Media Verification Placeholder
echo "6. Testing Media Verification (Placeholder)..."
echo "   POST /api/v1/verify/media"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/verify/media" \
  -H "Content-Type: application/json" \
  -d '{
    "media_url": "https://example.com/suspicious-video.mp4",
    "media_type": "video",
    "sender_id": "test_user_media",
    "county": "Nairobi"
  }' | python -m json.tool 2>/dev/null || curl -s -X POST "${BASE_URL}/api/v1/verify/media" \
  -H "Content-Type: application/json" \
  -d '{"media_url": "https://example.com/suspicious-video.mp4", "media_type": "video", "sender_id": "test_user_media", "county": "Nairobi"}'
echo ""
echo ""

echo "========================================"
echo "Tests Complete!"
echo "========================================"
echo ""
echo "Expected n8n Response Structure:"
echo "--------------------------------"
cat << 'EOF'
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "messages": {
    "english": "Warning/Caution/Safe message...",
    "swahili": "Onyo/Tahadhari/Salama message...",
    "sheng": "Heads up/Be careful/Poa message..."
  },
  "report_id": "firestore_document_id",
  "prebunking_tip": "For official election results, always visit iebc.or.ke",
  "scores": {
    "toxicity": 0.0-1.0,
    "severe_toxicity": 0.0-1.0,
    "obscene": 0.0-1.0,
    "identity_attack": 0.0-1.0,
    "insult": 0.0-1.0,
    "threat": 0.0-1.0
  },
  "matched_keyword": "madoadoa" | null
}
EOF
echo ""
echo "n8n Integration Notes:"
echo "----------------------"
echo "1. Use HTTP Request node to POST to /api/v1/verify/text"
echo "2. Parse response.risk_level to determine action"
echo "3. Use response.messages.swahili or .sheng based on user preference"
echo "4. Always include response.prebunking_tip in replies"
echo "5. Log response.report_id for tracking"

