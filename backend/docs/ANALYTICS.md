# Analytics Documentation for Project Mwavuli

This document provides comprehensive guidance on using the Mwavuli Analytics API for data analysis, pattern discovery, and insights generation.

## Table of Contents

1. [Overview](#overview)
2. [Use Cases](#use-cases)
3. [API Reference](#api-reference)
4. [Query Examples](#query-examples)
5. [Best Practices](#best-practices)
6. [Performance Considerations](#performance-considerations)
7. [Data Interpretation](#data-interpretation)

---

## Overview

The Mwavuli Analytics API provides 9 endpoints for analyzing content verification reports stored in Firestore. These endpoints enable:

- **Pattern Discovery**: Identify trends and anomalies in harmful content
- **Geographic Analysis**: Understand regional risk patterns
- **Temporal Analysis**: Discover time-based patterns
- **Detection Effectiveness**: Evaluate model performance
- **Data Export**: Export data for external analysis tools

---

## Use Cases

### 1. Real-Time Monitoring Dashboard

**Goal**: Monitor content verification activity in real-time

**Endpoints Used**:
- `/api/v1/analytics/summary` - Overall statistics
- `/api/v1/analytics/risk-distribution` - Current risk breakdown
- `/api/v1/analytics/hourly-patterns` - Recent activity patterns

**Example Query**:
```bash
# Get current day summary
curl "http://localhost:8000/api/v1/analytics/summary?start_date=2024-01-15&end_date=2024-01-15"
```

**Use Case**: Display on a monitoring dashboard that refreshes every 5 minutes.

### 2. Weekly Risk Report

**Goal**: Generate weekly reports for stakeholders

**Endpoints Used**:
- `/api/v1/analytics/summary` - Overall metrics
- `/api/v1/analytics/county-analysis` - County-level breakdown
- `/api/v1/analytics/keyword-trends` - Top keywords
- `/api/v1/export/reports` - Detailed data export

**Example Query**:
```bash
# Get last week's data
curl "http://localhost:8000/api/v1/analytics/summary?start_date=2024-01-08&end_date=2024-01-14"
curl "http://localhost:8000/api/v1/export/reports?format=csv&start_date=2024-01-08&end_date=2024-01-14" -o weekly_report.csv
```

**Use Case**: Automated weekly email reports with CSV attachments.

### 3. Geographic Risk Assessment

**Goal**: Identify high-risk counties for targeted interventions

**Endpoints Used**:
- `/api/v1/analytics/geographic-heatmap` - County risk scores
- `/api/v1/analytics/county-analysis` - Detailed county breakdown

**Example Query**:
```bash
# Get county risk heatmap
curl "http://localhost:8000/api/v1/analytics/geographic-heatmap?start_date=2024-01-01&end_date=2024-01-31"
```

**Use Case**: Visualize on a map to identify hotspots requiring attention.

### 4. Temporal Pattern Analysis

**Goal**: Understand when harmful content is most active

**Endpoints Used**:
- `/api/v1/analytics/hourly-patterns` - Hour-based patterns
- `/api/v1/analytics/daily-patterns` - Day-of-week patterns
- `/api/v1/analytics/toxicity-trends` - Long-term trends

**Example Query**:
```bash
# Analyze hourly patterns for last month
curl "http://localhost:8000/api/v1/analytics/hourly-patterns?start_date=2024-01-01&end_date=2024-01-31"
```

**Use Case**: Optimize monitoring schedules based on peak hours.

### 5. Model Performance Evaluation

**Goal**: Assess detection method effectiveness

**Endpoints Used**:
- `/api/v1/analytics/detection-comparison` - Lexicon vs Gemini
- `/api/v1/analytics/summary` - Overall statistics

**Example Query**:
```bash
# Compare detection methods
curl "http://localhost:8000/api/v1/analytics/detection-comparison?start_date=2024-01-01&end_date=2024-01-31"
```

**Use Case**: Monthly model performance reviews to improve detection accuracy.

### 6. Keyword Trend Monitoring

**Goal**: Track emerging harmful keywords

**Endpoints Used**:
- `/api/v1/analytics/keyword-trends` - Top keywords
- `/api/v1/export/analytics?analytics_type=keyword_trends` - Export for analysis

**Example Query**:
```bash
# Get top 50 keywords
curl "http://localhost:8000/api/v1/analytics/keyword-trends?limit=50&start_date=2024-01-01&end_date=2024-01-31"
```

**Use Case**: Update lexicon with new high-risk keywords discovered in data.

### 7. Anomaly Detection

**Goal**: Identify unusual spikes or patterns

**Endpoints Used**:
- `/api/v1/analytics/summary` - Overall stats
- `/api/v1/analytics/toxicity-trends` - Trend analysis
- Custom analysis on exported data

**Example Query**:
```bash
# Get toxicity trends to identify spikes
curl "http://localhost:8000/api/v1/analytics/toxicity-trends?days=90"
```

**Use Case**: Alert system for unusual activity requiring immediate attention.

---

## API Reference

### Summary Statistics

**Endpoint**: `GET /api/v1/analytics/summary`

**Description**: Returns overall statistics including total reports, risk distribution, average toxicity, top keywords, and top counties.

**Query Parameters**:
- `start_date` (optional): Start date in ISO format (YYYY-MM-DD)
- `end_date` (optional): End date in ISO format (YYYY-MM-DD)

**Response Example**:
```json
{
  "total_reports": 1250,
  "risk_distribution": {
    "HIGH": 150,
    "MEDIUM": 300,
    "LOW": 800
  },
  "avg_toxicity": 0.425,
  "top_keywords": [
    {"keyword": "madoadoa", "count": 45},
    {"keyword": "kwekwe", "count": 32}
  ],
  "top_counties": [
    {"county": "Nairobi", "count": 450},
    {"county": "Mombasa", "count": 200}
  ]
}
```

### Risk Distribution

**Endpoint**: `GET /api/v1/analytics/risk-distribution`

**Description**: Returns count of reports by risk level.

**Query Parameters**:
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response Example**:
```json
{
  "distribution": {
    "HIGH": 150,
    "MEDIUM": 300,
    "LOW": 800,
    "UNKNOWN": 0
  },
  "total": 1250
}
```

### County Analysis

**Endpoint**: `GET /api/v1/analytics/county-analysis`

**Description**: Returns county-level risk breakdown with percentages.

**Query Parameters**:
- `county` (optional): Filter by specific county
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response Example**:
```json
{
  "counties": {
    "Nairobi": {
      "HIGH": 50,
      "MEDIUM": 100,
      "LOW": 300,
      "total": 450,
      "high_percentage": 11.11,
      "medium_percentage": 22.22,
      "low_percentage": 66.67
    }
  }
}
```

### Keyword Trends

**Endpoint**: `GET /api/v1/analytics/keyword-trends`

**Description**: Returns most frequently matched keywords.

**Query Parameters**:
- `limit` (optional, default: 20): Maximum number of keywords (1-100)
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response Example**:
```json
{
  "keywords": [
    {"keyword": "madoadoa", "count": 45},
    {"keyword": "kwekwe", "count": 32},
    {"keyword": "toeni", "count": 28}
  ],
  "total_keywords": 3
}
```

### Toxicity Trends

**Endpoint**: `GET /api/v1/analytics/toxicity-trends`

**Description**: Returns daily average toxicity scores over time.

**Query Parameters**:
- `days` (optional, default: 30): Number of days to analyze (1-365)
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response Example**:
```json
{
  "trends": [
    {"date": "2024-01-01", "avg_toxicity": 0.425, "count": 50},
    {"date": "2024-01-02", "avg_toxicity": 0.380, "count": 45}
  ],
  "period_days": 30
}
```

### Hourly Patterns

**Endpoint**: `GET /api/v1/analytics/hourly-patterns`

**Description**: Returns risk distribution by hour of day (0-23).

**Response Example**:
```json
{
  "patterns": {
    "14": {
      "HIGH": 10,
      "MEDIUM": 15,
      "LOW": 25,
      "total": 50,
      "high_percentage": 20.0,
      "medium_percentage": 30.0,
      "low_percentage": 50.0
    }
  },
  "pattern_type": "hourly"
}
```

### Daily Patterns

**Endpoint**: `GET /api/v1/analytics/daily-patterns`

**Description**: Returns risk distribution by day of week.

**Response Example**:
```json
{
  "patterns": {
    "Monday": {
      "HIGH": 20,
      "MEDIUM": 40,
      "LOW": 100,
      "total": 160,
      "high_percentage": 12.5,
      "medium_percentage": 25.0,
      "low_percentage": 62.5
    }
  },
  "pattern_type": "daily"
}
```

### Detection Comparison

**Endpoint**: `GET /api/v1/analytics/detection-comparison`

**Description**: Compares Gemini vs Lexicon detection effectiveness.

**Response Example**:
```json
{
  "comparison": {
    "lexicon_detected": 100,
    "gemini_detected": 50,
    "both_detected": 30,
    "neither_detected": 20,
    "total": 200,
    "lexicon_percentage": 50.0,
    "gemini_percentage": 25.0,
    "both_percentage": 15.0,
    "neither_percentage": 10.0
  }
}
```

### Geographic Heatmap

**Endpoint**: `GET /api/v1/analytics/geographic-heatmap`

**Description**: Returns county-level risk scores for heatmap visualization.

**Response Example**:
```json
{
  "counties": {
    "Nairobi": {
      "HIGH": 50,
      "MEDIUM": 100,
      "LOW": 300,
      "total": 450,
      "avg_toxicity": 0.425,
      "risk_score": 1.78,
      "high_percentage": 11.11
    }
  }
}
```

---

## Query Examples

### Example 1: Last 7 Days Summary

```bash
# Calculate date range
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)

# Get summary
curl "http://localhost:8000/api/v1/analytics/summary?start_date=${START_DATE}&end_date=${END_DATE}"
```

### Example 2: High-Risk Counties This Month

```bash
# Get county analysis
curl "http://localhost:8000/api/v1/analytics/county-analysis?start_date=2024-01-01&end_date=2024-01-31" | \
  jq '.counties | to_entries | sort_by(.value.high_percentage) | reverse | .[0:5]'
```

### Example 3: Peak Hours Analysis

```bash
# Get hourly patterns
curl "http://localhost:8000/api/v1/analytics/hourly-patterns" | \
  jq '.patterns | to_entries | map({hour: .key, high_risk: .value.HIGH}) | sort_by(.high_risk) | reverse | .[0:5]'
```

### Example 4: Export Data for Analysis

```bash
# Export last month's reports
curl "http://localhost:8000/api/v1/export/reports?format=csv&start_date=2024-01-01&end_date=2024-01-31" \
  -o january_reports.csv

# Export keyword trends
curl "http://localhost:8000/api/v1/export/analytics?analytics_type=keyword_trends" \
  -o keyword_trends.csv
```

### Example 5: Compare Detection Methods

```bash
# Get detection comparison
curl "http://localhost:8000/api/v1/analytics/detection-comparison?start_date=2024-01-01&end_date=2024-01-31" | \
  jq '{lexicon: .comparison.lexicon_percentage, gemini: .comparison.gemini_percentage, both: .comparison.both_percentage}'
```

---

## Best Practices

### 1. Use Date Ranges

Always specify date ranges for better performance and relevant results:

```bash
# Good
curl "http://localhost:8000/api/v1/analytics/summary?start_date=2024-01-01&end_date=2024-01-31"

# Avoid (queries all data)
curl "http://localhost:8000/api/v1/analytics/summary"
```

### 2. Cache Frequently Used Queries

For dashboards that refresh frequently, cache results:

```python
# Example: Cache summary for 5 minutes
import time
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cached_summary(start_date, end_date):
    # Cache expires after 5 minutes
    return analytics.get_summary_stats(start_date, end_date)
```

### 3. Use Export Endpoints Sparingly

Export endpoints are designed for occasional analyst use, not for dashboards:

- Always provide `start_date` and `end_date` and keep windows bounded.
- Prefer the aggregate-backed `/api/v1/analytics/*` endpoints for dashboards.
- Use `/api/v1/export/*` and STIX export only when you explicitly need raw data outside Mwavuli.

### 4. Combine Multiple Endpoints

Combine data from multiple endpoints for comprehensive analysis:

```python
# Get summary
summary = requests.get(f"{BASE_URL}/api/v1/analytics/summary").json()

# Get county breakdown
counties = requests.get(f"{BASE_URL}/api/v1/analytics/county-analysis").json()

# Get keyword trends
keywords = requests.get(f"{BASE_URL}/api/v1/analytics/keyword-trends?limit=10").json()

# Combine for comprehensive report
```

### 5. Monitor Performance

Track query performance and optimize:

- Use date filters to limit data
- Use export endpoints for bulk analysis
- Consider BigQuery export for very large datasets

### 7. Firestore usage guardrails (for developers)

- New analytics features should be built against the `report_aggregates` collection via helpers in `utils/analytics.py` rather than scanning raw `reports` with `query_ref.stream()`.
- Raw `reports` scans are reserved for:
  - one-off maintenance or backfill scripts under `backend/scripts/`, or
  - low-frequency analyst/admin tools that are clearly documented as heavy.
- When reviewing changes, treat new uses of `.stream()` over `reports` as a red flag and consider whether an aggregate-based approach is more appropriate.

### 6. Handle Empty Results Gracefully

Always check for empty results:

```python
response = requests.get(f"{BASE_URL}/api/v1/analytics/keyword-trends").json()
if response["total_keywords"] == 0:
    print("No keywords found in the specified date range")
else:
    # Process keywords
    pass
```

---

## Performance Considerations

### Query Optimization

1. **Use Date Filters**: Always specify date ranges to limit data scanned
2. **Limit Results**: Use `limit` parameter for keyword trends
3. **Use Export Endpoints**: For large datasets, export and analyze locally
4. **Cache Results**: Cache frequently accessed analytics

### Firestore Indexing

Create composite indexes for common queries:

```bash
# Index for timestamp + risk_level queries
gcloud firestore indexes create \
  --collection-group=reports \
  --query-scope=COLLECTION \
  --field-config field-path=timestamp,order=DESCENDING \
  --field-config field-path=risk_level,order=ASCENDING
```

### Expected Response Times

- **Summary**: < 1 second (with date filter)
- **Risk Distribution**: < 1 second
- **County Analysis**: < 2 seconds
- **Keyword Trends**: < 2 seconds
- **Toxicity Trends**: < 3 seconds (30 days)
- **Geographic Heatmap**: < 3 seconds
- **Export (1000 reports)**: < 5 seconds

---

## Data Interpretation

### Risk Levels

- **HIGH**: Immediate attention required, contains high-risk keywords or toxicity > 0.7
- **MEDIUM**: Monitor closely, toxicity between 0.4-0.7
- **LOW**: Generally safe, toxicity < 0.4

### Toxicity Scores

- **0.0 - 0.3**: Low toxicity, generally safe content
- **0.3 - 0.5**: Moderate toxicity, may require review
- **0.5 - 0.7**: High toxicity, likely harmful
- **0.7 - 1.0**: Very high toxicity, definitely harmful

### Detection Methods

- **lexicon**: Matched high-risk keyword (highest confidence)
- **gemini**: Detected by Gemini context analysis
- **detoxify**: Detected by Detoxify toxicity model
- **combined**: Multiple methods detected the same content

### Geographic Risk Scores

Risk score calculation: `(HIGH × 3 + MEDIUM × 2 + LOW × 1) / total`

- **0.0 - 1.0**: Low risk county
- **1.0 - 2.0**: Medium risk county
- **2.0 - 3.0**: High risk county

---

## Troubleshooting

### Slow Queries

**Problem**: Analytics queries are slow

**Solutions**:
1. Add date filters to limit data
2. Use export endpoints for bulk analysis
3. Check Firestore indexes are created
4. Consider BigQuery export for very large datasets

### Missing Data

**Problem**: Expected data not appearing

**Solutions**:
1. Check date range includes data
2. Verify reports are being saved correctly
3. Check Firestore collection path
4. Review data in Firebase Console

### Incorrect Results

**Problem**: Analytics results seem incorrect

**Solutions**:
1. Verify date filters are correct
2. Check data quality in Firestore
3. Review field mappings
4. Test with known data

---

## Additional Resources

- [Looker Studio Setup Guide](LOOKER_STUDIO_SETUP.md)
- [API Documentation](http://localhost:8000/docs)
- [Firebase Firestore Documentation](https://firebase.google.com/docs/firestore)

