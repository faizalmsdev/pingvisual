# Web Change Monitor API Documentation

## Overview
This API allows you to create, manage, and monitor web change detection jobs. Each job monitors a specific URL at defined intervals and detects changes using AI analysis.

## Base URL
```
http://localhost:8000
```

## API Endpoints

### 1. Health Check
**GET** `/api/health`

Check if the API is running.

**Response:**
```json
{
  "success": true,
  "message": "Web Change Monitor API is running",
  "timestamp": "2025-01-31T10:30:00.000000"
}
```

### 2. System Status
**GET** `/api/status`

Get overall system status and job statistics.

**Response:**
```json
{
  "success": true,
  "status": {
    "total_jobs": 3,
    "running_jobs": 1,
    "paused_jobs": 0,
    "stopped_jobs": 2,
    "error_jobs": 0,
    "ai_enabled": true,
    "system_time": "2025-01-31T10:30:00.000000"
  }
}
```

### 3. Create Job
**POST** `/api/jobs`

Create a new monitoring job.

**Request Body:**
```json
{
  "name": "Caspian Equity Portfolio",
  "url": "https://example.com/portfolio",
  "check_interval_minutes": 5
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Caspian Equity Portfolio",
    "url": "https://example.com/portfolio",
    "check_interval_minutes": 5,
    "created_at": "2025-01-31T10:30:00.000000",
    "status": "created",
    "last_check": null,
    "total_checks": 0,
    "changes_detected": 0,
    "error_message": null
  },
  "message": "Job \"Caspian Equity Portfolio\" created successfully"
}
```

### 4. Get All Jobs
**GET** `/api/jobs`

Retrieve all monitoring jobs.

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Caspian Equity Portfolio",
      "url": "https://example.com/portfolio",
      "check_interval_minutes": 5,
      "created_at": "2025-01-31T10:30:00.000000",
      "status": "running",
      "last_check": "2025-01-31T10:35:00.000000",
      "total_checks": 2,
      "changes_detected": 1,
      "error_message": null
    }
  ],
  "total": 1
}
```

### 5. Get Specific Job
**GET** `/api/jobs/{job_id}`

Get details for a specific job.

**Response:**
```json
{
  "success": true,
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Caspian Equity Portfolio",
    "url": "https://example.com/portfolio",
    "check_interval_minutes": 5,
    "created_at": "2025-01-31T10:30:00.000000",
    "status": "running",
    "last_check": "2025-01-31T10:35:00.000000",
    "total_checks": 2,
    "changes_detected": 1,
    "error_message": null
  }
}
```

### 6. Start Job
**POST** `/api/jobs/{job_id}/start`

Start monitoring for a specific job.

**Request Body (Optional):**
```json
{
  "api_key": "your-openrouter-api-key"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Job \"Caspian Equity Portfolio\" started successfully",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Caspian Equity Portfolio",
    "status": "running",
    "last_check": null,
    "total_checks": 0
  }
}
```

### 7. Stop Job
**POST** `/api/jobs/{job_id}/stop`

Stop monitoring for a specific job.

**Response:**
```json
{
  "success": true,
  "message": "Job \"Caspian Equity Portfolio\" stopped successfully",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Caspian Equity Portfolio",
    "status": "stopped"
  }
}
```

### 8. Pause Job
**POST** `/api/jobs/{job_id}/pause`

Pause monitoring for a specific job.

**Response:**
```json
{
  "success": true,
  "message": "Job \"Caspian Equity Portfolio\" paused successfully",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Caspian Equity Portfolio",
    "status": "paused"
  }
}
```

### 9. Delete Job
**DELETE** `/api/jobs/{job_id}`

Delete a job and all its results.

**Response:**
```json
{
  "success": true,
  "message": "Job \"Caspian Equity Portfolio\" deleted successfully"
}
```

### 10. Get Job Results
**GET** `/api/jobs/{job_id}/results?limit=50`

Get detected changes for a specific job.

**Query Parameters:**
- `limit` (optional): Number of results to return (default: 50)

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_name": "Caspian Equity Portfolio",
  "results": [
    {
      "type": "new_images",
      "description": "2 new images found",
      "details": [
        {
          "src": "https://example.com/company-logo.jpg",
          "alt": "ACME Corp Logo",
          "title": "ACME Corporation",
          "context": "Alt: 'ACME Corp Logo' | Title: 'ACME Corporation'"
        }
      ],
              "ai_analysis": {
        "new_companies_detected": true,
        "companies": [
          {
            "name": "ACME Corp",
            "sector": "Technology",
            "confidence": "high",
            "evidence": "New logo image with alt text containing company name",
            "source": "image"
          }
        ],
        "added_company": "ACME Corp",
        "removed_company": null,
        "modified_company": null,
        "analysis_summary": "New portfolio company detected from image addition"
      },
      "timestamp": "2025-01-31T10:35:00.000000",
      "detected_at": "2025-01-31T10:35:00.000000"
    }
  ],
  "total_results": 1
}
```

### 11. Get Job Statistics
**GET** `/api/jobs/{job_id}/stats`

Get comprehensive statistics for a specific job.

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_name": "Caspian Equity Portfolio",
  "stats": {
    "total_checks": 10,
    "total_changes": 3,
    "changes_detected": 3,
    "last_check": "2025-01-31T11:00:00.000000",
    "status": "running",
    "created_at": "2025-01-31T10:30:00.000000",
    "error_message": null,
    "change_types": {
      "new_images": 2,
      "text_change": 1
    },
    "ai_detections": 2,
    "companies_detected": ["ACME Corp", "TechStart Inc"]
  }
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid input)
- `404` - Not Found (job doesn't exist)
- `500` - Internal Server Error

## Postman Testing Guide

### Step 1: Set Up Environment
1. Create a new Postman environment
2. Add variable: `base_url` = `http://localhost:8000`
3. Add variable: `api_key` = `your-openrouter-api-key` (optional)

### Step 2: Test Basic Functionality

#### 1. Health Check
```
GET {{base_url}}/api/health
```

#### 2. Create a Job
```
POST {{base_url}}/api/jobs
Content-Type: application/json

{
  "name": "Test Portfolio Monitor",
  "url": "http://127.0.0.1:3001/caspianequity.html",
  "check_interval_minutes": 2
}
```
*Save the `job_id` from response for next steps*

#### 3. Start the Job
```
POST {{base_url}}/api/jobs/{{job_id}}/start
Content-Type: application/json

{
  "api_key": "{{api_key}}"
}
```

#### 4. Check Job Status
```
GET {{base_url}}/api/jobs/{{job_id}}
```

#### 5. Get All Jobs
```
GET {{base_url}}/api/jobs
```

#### 6. Wait and Check Results
*Wait for a few minutes (longer than your check_interval_minutes)*
```
GET {{base_url}}/api/jobs/{{job_id}}/results?limit=10
```

#### 7. Get Job Statistics
```
GET {{base_url}}/api/jobs/{{job_id}}/stats
```

#### 8. System Status
```
GET {{base_url}}/api/status
```

### Step 3: Test Job Management

#### Pause Job
```
POST {{base_url}}/api/jobs/{{job_id}}/pause
```

#### Resume Job (Start Again)
```
POST {{base_url}}/api/jobs/{{job_id}}/start
```

#### Stop Job
```
POST {{base_url}}/api/jobs/{{job_id}}/stop
```

#### Delete Job
```
DELETE {{base_url}}/api/jobs/{{job_id}}
```

## File Structure

The API creates the following files and directories:

```
├── api_monitor.py          # Main API file
├── paste.py               # Original monitor classes (imported)
├── jobs.json              # Job configurations storage
├── results/               # Directory for storing results
│   ├── {job_id}.json     # Results for each job
│   └── ...
└── .env                   # Environment variables (API_KEY)
```

## Usage Examples

### Example 1: Monitor a Portfolio Website Every 5 Minutes
```bash
# Create job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Caspian Equity Monitor",
    "url": "https://caspianequity.com/portfolio",
    "check_interval_minutes": 5
  }'

# Start monitoring (with AI)
curl -X POST http://localhost:8000/api/jobs/{job_id}/start \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'

# Check results after some time
curl http://localhost:8000/api/jobs/{job_id}/results
```

### Example 2: Quick Status Check
```bash
# Get system status
curl http://localhost:8000/api/status

# Get specific job stats
curl http://localhost:8000/api/jobs/{job_id}/stats
```

## Environment Setup

1. Set up environment variables:
```bash
export API_KEY="your-openrouter-api-key"
```

2. Or create a `.env` file:
```
API_KEY=your-openrouter-api-key
```

3. Run the API:
```bash
python api_monitor.py
```

## Job Status States

- `created` - Job created but not started
- `running` - Job is actively monitoring
- `paused` - Job temporarily stopped
- `stopped` - Job manually stopped
- `error` - Job encountered an error

## AI Analysis Features

When an API key is provided, the system will:
- Analyze detected changes using DeepSeek AI
- Identify new portfolio companies
- Detect company additions/removals
- Provide confidence scores and evidence
- Categorize companies by sector/industry

## Rate Limiting and Performance

- Each job runs in its own thread
- Results are stored in JSON files
- Memory usage is controlled (max 200 results per job, 50 changes in memory)
- Chrome browser instances are managed per job
- Automatic cleanup on job deletion

## Troubleshooting

### Common Issues:

1. **Job won't start**: Check if URL is accessible and Chrome driver is installed
2. **No AI analysis**: Verify API_KEY is set correctly
3. **Results not appearing**: Wait for at least one check interval + initial delay
4. **Memory issues**: Jobs automatically clean up old results
5. **Port conflicts**: Change port in `app.run()` if 8000 is occupied

### Debug Endpoints:

Check logs in the console where you started the API server for detailed information about job execution and errors.