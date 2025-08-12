# Basic Authentication Example
from flask import Flask, request, jsonify
from functools import wraps
import base64

def require_basic_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Basic '):
            return jsonify({'error': 'Basic authentication required'}), 401
        
        try:
            # Decode base64 credentials
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            email, password = credentials.split(':', 1)
            
            # Authenticate user
            user = user_manager.authenticate_user(email, password)
            if not user:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Store user in request context
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception:
            return jsonify({'error': 'Invalid authorization header'}), 401
    
    return decorated_function

# Usage:
# curl -X GET http://localhost:5000/api/jobs \
#      -H "Authorization: Basic $(echo -n 'user@example.com:password123' | base64)"
