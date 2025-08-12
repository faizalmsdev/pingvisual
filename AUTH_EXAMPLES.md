# Web Monitor API - Authentication Examples

## 1. Register a new user
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Response includes `token` field with your user_id:
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "user_id": "abc123-def456-ghi789",
    "email": "user@example.com",
    "created_at": "2025-08-12T10:30:00"
  },
  "token": "abc123-def456-ghi789"
}
```

## 2. Login (Session-based)
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}' \
  -c cookies.txt
```

## 3. Use API with Session Cookies
```bash
curl -X GET http://localhost:5000/api/jobs \
  -b cookies.txt
```

## 4. Use API with Bearer Token
```bash
curl -X GET http://localhost:5000/api/jobs \
  -H "Authorization: Bearer YOUR_USER_ID"
```

## 5. Use API with Custom Header
```bash
curl -X GET http://localhost:5000/api/jobs \
  -H "X-User-Token: YOUR_USER_ID"
```

## 6. Use API with Query Parameter
```bash
curl -X GET "http://localhost:5000/api/jobs?token=YOUR_USER_ID"
```

## 7. Create a Job with Token
```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_USER_ID" \
  -d '{
    "name": "My Website Monitor",
    "url": "https://example.com",
    "check_interval_minutes": 5
  }'
```

## 8. Start a Job
```bash
curl -X POST http://localhost:5000/api/jobs/JOB_ID/start \
  -H "Authorization: Bearer YOUR_USER_ID"
```

## 9. Get Job Results
```bash
curl -X GET http://localhost:5000/api/jobs/JOB_ID/results \
  -H "Authorization: Bearer YOUR_USER_ID"
```

## 10. Get User Profile
```bash
curl -X GET http://localhost:5000/api/auth/profile \
  -H "Authorization: Bearer YOUR_USER_ID"
```

## Authentication Priority
The API checks for authentication in this order:
1. Session cookie (if logged in via web interface)
2. Authorization: Bearer TOKEN header
3. X-User-Token: TOKEN header  
4. token=TOKEN query parameter

## Notes
- Replace `YOUR_USER_ID` with the actual user_id from registration/login response
- The user_id serves as your authentication token
- All authenticated endpoints work with any of the 4 authentication methods
- Session cookies are automatically handled by browsers
- Tokens are better for API clients and automation
