# API Key Authentication Example
from flask import Flask, request, jsonify
from functools import wraps
import secrets

# Add to User class - generate API key for each user
def generate_api_key():
    return secrets.token_urlsafe(32)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Find user by API key
        user = None
        for u in user_manager.users.values():
            if hasattr(u, 'api_key') and u.api_key == api_key:
                user = u
                break
        
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid API key'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

# Usage:
# curl -X GET http://localhost:5000/api/jobs \
#      -H "X-API-Key: your_api_key_here"
