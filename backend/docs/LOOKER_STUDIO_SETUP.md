# Looker Studio Setup Guide for Project Mwavuli

This guide walks you through setting up Looker Studio dashboards to visualize Mwavuli content verification data.

## Table of Contents

1. [Connection Methods](#connection-methods)
2. [Direct Firestore Connection](#direct-firestore-connection)
3. [BigQuery Export Setup (Optional)](#bigquery-export-setup-optional)
4. [API-Based Export](#api-based-export)
5. [Dashboard Templates](#dashboard-templates)
6. [Calculated Fields](#calculated-fields)
7. [Troubleshooting](#troubleshooting)

---

## Connection Methods

There are three ways to connect Looker Studio to Mwavuli data:

1. **Direct Firestore Connection** (Recommended for small-medium datasets)
2. **BigQuery Export** (Recommended for large datasets or advanced analytics)
3. **API-Based Export** (For custom data views or scheduled exports)

---

## Direct Firestore Connection

### Prerequisites

- Firebase project with Firestore enabled
- Looker Studio account (free)
- Access to Firebase project

### Step-by-Step Setup

1. **Open Looker Studio**
   - Go to [lookerstudio.google.com](https://lookerstudio.google.com)
   - Sign in with your Google account

2. **Create New Data Source**
   - Click **Create** → **Data Source**
   - Search for **"Firebase"** or **"Firestore"**
   - Select **Firebase Firestore**

3. **Configure Connection**
   - **Project ID**: Enter your Firebase project ID (e.g., `mwavuli-nira`)
   - **Database ID**: Enter your custom database ID (e.g., `mwavuli-nira-db`) or leave empty for default
   - **Collection Path**: `artifacts/mwavuli/public/data/reports`
   - Click **Connect**

4. **Authenticate**
   - Sign in with a Google account that has access to the Firebase project
   - Grant necessary permissions

5. **Configure Fields**
   - Looker Studio will automatically detect fields
   - Review and adjust field types as needed (see [Calculated Fields](#calculated-fields))

6. **Create Report**
   - Click **Create Report**
   - Start building your dashboard

### Field Mapping

The following fields are available in Firestore:

| Field Name | Type | Description |
|------------|------|-------------|
| `text` | Text | Original text content |
| `risk_level` | Text | HIGH, MEDIUM, LOW, UNKNOWN |
| `language` | Text | Detected language |
| `county` | Text | Kenyan county |
| `region` | Text | Geographic region |
| `is_urban` | Boolean | Urban/rural classification |
| `timestamp` | Date & Time | Report timestamp |
| `hour_of_day` | Number | Hour (0-23) |
| `day_of_week` | Text | Day name |
| `is_weekend` | Boolean | Weekend flag |
| `text_length` | Number | Character count |
| `word_count` | Number | Word count |
| `has_urls` | Boolean | Contains URLs |
| `has_mentions` | Boolean | Contains @ or # |
| `detection_method` | Text | lexicon, detoxify, gemini, combined |
| `confidence_score` | Number | Detection confidence (0-1) |
| `matched_keyword` | Text | Matched lexicon keyword |
| `gemini_context_flag` | Boolean | Gemini-detected flag |
| `scores` | Record | Nested toxicity scores |
| `sender_hash` | Text | Anonymized sender ID |

---

## BigQuery Export Setup (Optional)

For large datasets or advanced analytics, export Firestore data to BigQuery.

### Step 1: Enable BigQuery Export

1. **Firebase Console**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Select your project
   - Navigate to **Firestore Database** → **Exports** tab

2. **Create Export**
   - Click **Export to BigQuery**
   - Select collections to export: `artifacts/mwavuli/public/data/reports`
   - Choose BigQuery dataset (create new if needed)
   - Set export schedule (daily recommended)
   - Click **Export**

### Step 2: Connect Looker Studio to BigQuery

1. **Create Data Source**
   - In Looker Studio, click **Create** → **Data Source**
   - Search for **"BigQuery"**
   - Select **BigQuery**

2. **Select Dataset**
   - Choose your project
   - Select the exported dataset
   - Select the `reports` table

3. **Configure Fields**
   - Review field types
   - Add calculated fields as needed

### Benefits of BigQuery

- **Performance**: Faster queries for large datasets
- **Advanced SQL**: Use SQL for complex aggregations
- **Scheduled Updates**: Automatic data refresh
- **Cost Efficiency**: Pay only for queries

---

## API-Based Export

Use the Mwavuli API export endpoints to get custom data views.

### Step 1: Export Data

```bash
# Export reports as CSV
curl "http://localhost:8000/api/v1/export/reports?format=csv&start_date=2024-01-01" \
  -o mwavuli_reports.csv

# Export analytics
curl "http://localhost:8000/api/v1/export/analytics?analytics_type=risk_distribution" \
  -o analytics.csv

# Export Looker Studio view
curl "http://localhost:8000/api/v1/export/looker-studio" \
  -o looker_studio_view.json
```

### Step 2: Import to Looker Studio

1. **Upload CSV**
   - In Looker Studio, click **Create** → **Data Source**
   - Select **File Upload** → **CSV**
   - Upload your exported CSV file

2. **Use Google Sheets**
   - Upload CSV to Google Sheets
   - In Looker Studio, connect to **Google Sheets**
   - Select your sheet

### Step 3: Schedule Updates (Optional)

Use Google Apps Script or scheduled jobs to:
- Periodically call export endpoints
- Update Google Sheets
- Refresh Looker Studio data source

---

## Dashboard Templates

### Page 1: Overview Dashboard

**Metrics:**
- Total Reports (metric card)
- High Risk Count (metric card)
- Average Toxicity Score (metric card)
- Detection Accuracy (metric card)

**Charts:**
- Risk Level Distribution (Pie Chart)
- Reports Over Time (Time Series Chart)
- Top 10 Counties (Bar Chart)
- Top 10 Keywords (Table)

**Filters:**
- Date Range
- County
- Risk Level

### Page 2: Content Analysis

**Charts:**
- Keyword Frequency (Word Cloud or Bar Chart)
- Toxicity Score Distribution (Histogram)
- Detection Method Comparison (Stacked Bar Chart)
- Language Distribution (Pie Chart)

**Tables:**
- Recent High-Risk Reports
- Keyword Trends Over Time

### Page 3: Geographic Analysis

**Charts:**
- County Risk Heatmap (Map Chart)
- Regional Trends (Line Chart)
- Urban vs Rural Comparison (Comparison Chart)
- County Risk Scores (Bar Chart)

**Filters:**
- Region
- Urban/Rural
- Date Range

### Page 4: Temporal Patterns

**Charts:**
- Hourly Patterns (Heatmap: Hour × Risk Level)
- Day of Week Analysis (Bar Chart)
- Weekend vs Weekday (Comparison Chart)
- Peak Hours Identification (Line Chart)

**Insights:**
- Peak hours for high-risk content
- Day-of-week patterns
- Weekend activity comparison

---

## Calculated Fields

Create these calculated fields in Looker Studio for enhanced analysis:

### Date Fields

```
Date Only
FORMAT_DATETIME("%Y-%m-%d", timestamp)

Hour
EXTRACT(HOUR FROM timestamp)

Day of Week Number
DAYOFWEEK(timestamp)

Is Weekend
CASE
  WHEN DAYOFWEEK(timestamp) IN (1, 7) THEN TRUE
  ELSE FALSE
END
```

### Toxicity Fields

```
Max Toxicity Score
CASE
  WHEN scores.toxicity IS NOT NULL THEN scores.toxicity
  WHEN scores.severe_toxicity IS NOT NULL THEN scores.severe_toxicity
  ELSE 0
END

Toxicity Category
CASE
  WHEN Max Toxicity Score > 0.7 THEN "High"
  WHEN Max Toxicity Score > 0.4 THEN "Medium"
  ELSE "Low"
END
```

### Geographic Fields

```
Region Group
CASE
  WHEN region IN ("Nairobi", "Central") THEN "Central Kenya"
  WHEN region IN ("Coast", "North Eastern") THEN "Coastal"
  WHEN region IN ("Rift Valley", "Western") THEN "Rift & Western"
  WHEN region IN ("Nyanza", "Eastern") THEN "Other"
  ELSE "Unknown"
END
```

### Detection Fields

```
Detection Source
CASE
  WHEN matched_keyword IS NOT NULL AND gemini_context_flag THEN "Both"
  WHEN matched_keyword IS NOT NULL THEN "Lexicon"
  WHEN gemini_context_flag THEN "Gemini"
  WHEN detection_method = "detoxify" THEN "Detoxify"
  ELSE "Unknown"
END

High Confidence Flag
CASE
  WHEN confidence_score > 0.8 THEN TRUE
  ELSE FALSE
END
```

### Content Fields

```
Content Type
CASE
  WHEN has_urls AND has_mentions THEN "Rich Content"
  WHEN has_urls THEN "With Links"
  WHEN has_mentions THEN "With Mentions"
  ELSE "Plain Text"
END

Text Length Category
CASE
  WHEN text_length < 50 THEN "Short"
  WHEN text_length < 200 THEN "Medium"
  ELSE "Long"
END
```

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Firestore
- **Solution**: Verify Firebase project ID and database ID
- **Solution**: Check that your Google account has Firebase access
- **Solution**: Ensure Firestore is enabled in Firebase Console

**Problem**: Fields not appearing
- **Solution**: Refresh the data source
- **Solution**: Check collection path is correct
- **Solution**: Verify data exists in Firestore

### Performance Issues

**Problem**: Slow dashboard loading
- **Solution**: Use BigQuery export for large datasets
- **Solution**: Add date filters to limit data
- **Solution**: Use pre-aggregated analytics endpoints

**Problem**: Query timeout
- **Solution**: Reduce date range
- **Solution**: Add indexes in Firestore
- **Solution**: Use API export endpoints instead

### Data Issues

**Problem**: Missing fields
- **Solution**: Check that reports have been saved with enhanced metadata
- **Solution**: Verify `save_report()` includes all fields
- **Solution**: Check Firestore document structure

**Problem**: Incorrect data types
- **Solution**: Manually set field types in Looker Studio
- **Solution**: Use calculated fields to convert types
- **Solution**: Check Firestore field values

---

## Best Practices

1. **Use Filters**: Always add date range filters to improve performance
2. **Cache Data**: Use BigQuery for frequently accessed data
3. **Schedule Updates**: Set up automatic data refresh
4. **Optimize Queries**: Use pre-aggregated analytics endpoints when possible
5. **Monitor Costs**: Track BigQuery usage if using export method
6. **Share Securely**: Control access to dashboards containing sensitive data

---

## Example Dashboard URLs

After creating your dashboard, you can share it via URL:

```
https://lookerstudio.google.com/reporting/[REPORT_ID]
```

Set appropriate sharing permissions:
- **Viewers**: Can view but not edit
- **Editors**: Can modify dashboard
- **Owners**: Full control

---

## Support

For issues or questions:
- Check Firebase Console for Firestore status
- Review Looker Studio documentation
- Contact the Mwavuli development team

