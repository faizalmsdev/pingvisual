# Simple Token Authentication Example
from flask import Flask, request, jsonify
from functools import wraps

def require_token_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header or query parameter
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]  # Remove 'Bearer ' prefix
        else:
            token = request.headers.get('X-User-Token') or request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Authentication token required'}), 401
        
        # Use token as user_id directly (simple approach)
        user = user_manager.get_user(token)
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

# Usage:
# curl -X GET http://localhost:5000/api/jobs \
#      -H "Authorization: Bearer user_id_here"
# or
# curl -X GET http://localhost:5000/api/jobs \
#      -H "X-User-Token: user_id_here"
# or
# curl -X GET "http://localhost:5000/api/jobs?token=user_id_here"
