#!/bin/bash
# Project Mwavuli - Analytics & Export API Test Script
# Run this script to test the analytics and export endpoints
#
# Prerequisites:
# 1. Start the server: uvicorn main:app --reload
# 2. Make this script executable: chmod +x test_analytics.sh
# 3. Run: ./test_analytics.sh

BASE_URL="http://localhost:8000"

echo "========================================"
echo "Project Mwavuli - Analytics & Export Tests"
echo "========================================"
echo ""

# Test 1: Summary Statistics
echo "1. Testing Summary Statistics..."
echo "   GET /api/v1/analytics/summary"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/summary" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/summary"
echo ""
echo ""

# Test 2: Risk Distribution
echo "2. Testing Risk Distribution..."
echo "   GET /api/v1/analytics/risk-distribution"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/risk-distribution" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/risk-distribution"
echo ""
echo ""

# Test 3: Risk Distribution with Date Range
echo "3. Testing Risk Distribution (with date range)..."
echo "   GET /api/v1/analytics/risk-distribution?start_date=2024-01-01&end_date=2024-12-31"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/risk-distribution?start_date=2024-01-01&end_date=2024-12-31" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/risk-distribution?start_date=2024-01-01&end_date=2024-12-31"
echo ""
echo ""

# Test 4: County Analysis
echo "4. Testing County Analysis..."
echo "   GET /api/v1/analytics/county-analysis"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/county-analysis" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/county-analysis"
echo ""
echo ""

# Test 5: County Analysis (filtered)
echo "5. Testing County Analysis (Nairobi only)..."
echo "   GET /api/v1/analytics/county-analysis?county=Nairobi"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/county-analysis?county=Nairobi" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/county-analysis?county=Nairobi"
echo ""
echo ""

# Test 6: Keyword Trends
echo "6. Testing Keyword Trends..."
echo "   GET /api/v1/analytics/keyword-trends?limit=10"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/keyword-trends?limit=10" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/keyword-trends?limit=10"
echo ""
echo ""

# Test 7: Toxicity Trends
echo "7. Testing Toxicity Trends..."
echo "   GET /api/v1/analytics/toxicity-trends?days=30"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/toxicity-trends?days=30" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/toxicity-trends?days=30"
echo ""
echo ""

# Test 8: Hourly Patterns
echo "8. Testing Hourly Patterns..."
echo "   GET /api/v1/analytics/hourly-patterns"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/hourly-patterns" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/hourly-patterns"
echo ""
echo ""

# Test 9: Daily Patterns
echo "9. Testing Daily Patterns..."
echo "   GET /api/v1/analytics/daily-patterns"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/daily-patterns" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/daily-patterns"
echo ""
echo ""

# Test 10: Detection Comparison
echo "10. Testing Detection Comparison..."
echo "    GET /api/v1/analytics/detection-comparison"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/detection-comparison" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/detection-comparison"
echo ""
echo ""

# Test 11: Geographic Heatmap
echo "11. Testing Geographic Heatmap..."
echo "    GET /api/v1/analytics/geographic-heatmap"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/analytics/geographic-heatmap" | python -m json.tool 2>/dev/null || curl -s -X GET "${BASE_URL}/api/v1/analytics/geographic-heatmap"
echo ""
echo ""

# Test 12: Export Reports (CSV)
echo "12. Testing Export Reports (CSV)..."
echo "    GET /api/v1/export/reports?format=csv"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/reports?format=csv" | head -20
echo ""
echo "(Showing first 20 lines of CSV output)"
echo ""

# Test 13: Export Reports (JSON)
echo "13. Testing Export Reports (JSON)..."
echo "    GET /api/v1/export/reports?format=json"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/reports?format=json" | python -m json.tool 2>/dev/null | head -30 || curl -s -X GET "${BASE_URL}/api/v1/export/reports?format=json" | head -30
echo ""
echo "(Showing first 30 lines of JSON output)"
echo ""

# Test 14: Export Reports (CSV with fields)
echo "14. Testing Export Reports (CSV with specific fields)..."
echo "    GET /api/v1/export/reports?format=csv&fields=risk_level,county,timestamp"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/reports?format=csv&fields=risk_level,county,timestamp" | head -10
echo ""
echo "(Showing first 10 lines)"
echo ""

# Test 15: Export Analytics (Risk Distribution)
echo "15. Testing Export Analytics (Risk Distribution)..."
echo "    GET /api/v1/export/analytics?analytics_type=risk_distribution"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/analytics?analytics_type=risk_distribution"
echo ""
echo ""

# Test 16: Export Analytics (County Analysis)
echo "16. Testing Export Analytics (County Analysis)..."
echo "    GET /api/v1/export/analytics?analytics_type=county_analysis"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/analytics?analytics_type=county_analysis" | head -20
echo ""
echo "(Showing first 20 lines)"
echo ""

# Test 17: Export Analytics (Keyword Trends)
echo "17. Testing Export Analytics (Keyword Trends)..."
echo "    GET /api/v1/export/analytics?analytics_type=keyword_trends"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/analytics?analytics_type=keyword_trends"
echo ""
echo ""

# Test 18: Export Analytics (Toxicity Trends)
echo "18. Testing Export Analytics (Toxicity Trends)..."
echo "    GET /api/v1/export/analytics?analytics_type=toxicity_trends"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/analytics?analytics_type=toxicity_trends" | head -20
echo ""
echo "(Showing first 20 lines)"
echo ""

# Test 19: Export Looker Studio View
echo "19. Testing Export Looker Studio View..."
echo "    GET /api/v1/export/looker-studio"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/looker-studio" | python -m json.tool 2>/dev/null | head -50 || curl -s -X GET "${BASE_URL}/api/v1/export/looker-studio" | head -50
echo ""
echo "(Showing first 50 lines of JSON output)"
echo ""

# Test 20: Export Looker Studio View (with date range)
echo "20. Testing Export Looker Studio View (with date range)..."
echo "    GET /api/v1/export/looker-studio?start_date=2024-01-01&end_date=2024-12-31"
echo "----------------------------------------"
curl -s -X GET "${BASE_URL}/api/v1/export/looker-studio?start_date=2024-01-01&end_date=2024-12-31" | python -m json.tool 2>/dev/null | head -30 || curl -s -X GET "${BASE_URL}/api/v1/export/looker-studio?start_date=2024-01-01&end_date=2024-12-31" | head -30
echo ""
echo ""

echo "========================================"
echo "Tests Complete!"
echo "========================================"
echo ""
echo "Analytics Endpoints Summary:"
echo "----------------------------"
echo "1. GET /api/v1/analytics/summary"
echo "2. GET /api/v1/analytics/risk-distribution"
echo "3. GET /api/v1/analytics/county-analysis"
echo "4. GET /api/v1/analytics/keyword-trends"
echo "5. GET /api/v1/analytics/toxicity-trends"
echo "6. GET /api/v1/analytics/hourly-patterns"
echo "7. GET /api/v1/analytics/daily-patterns"
echo "8. GET /api/v1/analytics/detection-comparison"
echo "9. GET /api/v1/analytics/geographic-heatmap"
echo ""
echo "Export Endpoints Summary:"
echo "------------------------"
echo "1. GET /api/v1/export/reports?format=csv|json"
echo "2. GET /api/v1/export/analytics?analytics_type=..."
echo "3. GET /api/v1/export/looker-studio"
echo ""
echo "Common Query Parameters:"
echo "------------------------"
echo "- start_date: YYYY-MM-DD (ISO format)"
echo "- end_date: YYYY-MM-DD (ISO format)"
echo "- county: Filter by county name"
echo "- limit: Number of results (keyword-trends)"
echo "- days: Number of days (toxicity-trends)"
echo "- format: csv or json (export endpoints)"
echo "- fields: Comma-separated field list (CSV export)"
echo "- analytics_type: risk_distribution, county_analysis, keyword_trends, toxicity_trends"

