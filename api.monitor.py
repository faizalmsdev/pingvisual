from flask import Flask, request, jsonify, session
from flask_cors import CORS
import json
import os
import uuid
import threading
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import logging
from functools import wraps

# Import the existing WebChangeMonitor class
from webmonitor import WebChangeMonitor, AIAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class User:
    user_id: str
    email: str
    password_hash: str
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True

@dataclass
class MonitoringJob:
    job_id: str
    user_id: str  # Added user_id to associate jobs with users
    name: str
    url: str
    check_interval_minutes: int
    created_at: str
    status: str  # 'created', 'running', 'paused', 'stopped', 'error'
    last_check: Optional[str] = None
    total_checks: int = 0
    changes_detected: int = 0
    error_message: Optional[str] = None

class UserManager:
    def __init__(self, users_file="users.json"):
        self.users_file = users_file
        self.users: Dict[str, User] = {}
        self.load_users()
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user = User(**user_data)
                        self.users[user.user_id] = user
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            users_data = [asdict(user) for user in self.users.values()]
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return any(user.email == email for user in self.users.values())
    
    def create_user(self, email: str, password: str) -> Optional[str]:
        """Create a new user"""
        if self.email_exists(email):
            return None
        
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        
        user = User(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            created_at=datetime.now().isoformat()
        )
        
        self.users[user_id] = user
        self.save_users()
        logger.info(f"Created user {user_id}: {email}")
        return user_id
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        for user in self.users.values():
            if user.email == email and user.is_active:
                if self.verify_password(password, user.password_hash):
                    user.last_login = datetime.now().isoformat()
                    self.save_users()
                    return user
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None

class JobManager:
    def __init__(self, jobs_file="jobs.json", results_dir="results"):
        self.jobs_file = jobs_file
        self.results_dir = results_dir
        self.jobs: Dict[str, MonitoringJob] = {}
        self.monitors: Dict[str, WebChangeMonitor] = {}
        self.monitor_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)
        
        # Load existing jobs
        self.load_jobs()
        
    def load_jobs(self):
        """Load jobs from JSON file"""
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                    for job_data in jobs_data:
                        # Handle jobs without user_id (for backward compatibility)
                        if 'user_id' not in job_data:
                            job_data['user_id'] = 'legacy'
                        job = MonitoringJob(**job_data)
                        self.jobs[job.job_id] = job
                logger.info(f"Loaded {len(self.jobs)} jobs from {self.jobs_file}")
        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
    
    def save_jobs(self):
        """Save jobs to JSON file"""
        try:
            jobs_data = [asdict(job) for job in self.jobs.values()]
            with open(self.jobs_file, 'w') as f:
                json.dump(jobs_data, f, indent=2)
            logger.info(f"Saved {len(self.jobs)} jobs to {self.jobs_file}")
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
    
    def create_job(self, user_id: str, name: str, url: str, check_interval_minutes: int) -> str:
        """Create a new monitoring job for a specific user"""
        job_id = str(uuid.uuid4())
        job = MonitoringJob(
            job_id=job_id,
            user_id=user_id,
            name=name,
            url=url,
            check_interval_minutes=check_interval_minutes,
            created_at=datetime.now().isoformat(),
            status='created'
        )
        self.jobs[job_id] = job
        self.save_jobs()
        logger.info(f"Created job {job_id}: {name} for user {user_id}")
        return job_id
    
    def get_user_jobs(self, user_id: str) -> List[MonitoringJob]:
        """Get all jobs for a specific user"""
        return [job for job in self.jobs.values() if job.user_id == user_id]
    
    def user_owns_job(self, user_id: str, job_id: str) -> bool:
        """Check if user owns the specified job"""
        job = self.jobs.get(job_id)
        return job is not None and job.user_id == user_id
    
    def start_job(self, job_id: str, api_key: Optional[str] = None) -> bool:
        """Start monitoring for a specific job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status == 'running':
            return True
        
        try:
            # Create monitor instance
            monitor = WebChangeMonitor(url=job.url, api_key=api_key)
            self.monitors[job_id] = monitor
            
            # Create stop event
            stop_event = threading.Event()
            self.stop_events[job_id] = stop_event
            
            # Create and start monitoring thread
            thread = threading.Thread(
                target=self._monitor_job,
                args=(job_id, stop_event),
                daemon=True
            )
            self.monitor_threads[job_id] = thread
            thread.start()
            
            # Update job status
            job.status = 'running'
            self.save_jobs()
            
            logger.info(f"Started monitoring job {job_id}")
            return True
            
        except Exception as e:
            job.status = 'error'
            job.error_message = str(e)
            self.save_jobs()
            logger.error(f"Error starting job {job_id}: {e}")
            return False
    
    def _monitor_job(self, job_id: str, stop_event: threading.Event):
        """Main monitoring loop for a job"""
        job = self.jobs[job_id]
        monitor = self.monitors[job_id]
        
        try:
            logger.info(f"Starting monitoring loop for job {job_id}")
            
            # Initial scrape
            monitor.current_content = monitor.scrape_page()
            if monitor.current_content:
                job.total_checks += 1
                job.last_check = datetime.now().isoformat()
                self.save_jobs()
                logger.info(f"Initial scrape completed for job {job_id}")
            
            # Wait for initial period before first comparison
            initial_wait = min(job.check_interval_minutes * 60, 120)  # Max 2 minutes
            if stop_event.wait(initial_wait):
                return
            
            while not stop_event.is_set():
                try:
                    # Scrape new content
                    new_content = monitor.scrape_page()
                    job.total_checks += 1
                    job.last_check = datetime.now().isoformat()
                    
                    if new_content and monitor.current_content:
                        # Compare with previous content
                        detected_changes = monitor.compare_content(monitor.current_content, new_content)
                        
                        if detected_changes:
                            job.changes_detected += len(detected_changes)
                            logger.info(f"Job {job_id}: {len(detected_changes)} changes detected")
                            
                            # Save changes to results file
                            self._save_results(job_id, detected_changes)
                            
                            # Update monitor's changes list
                            monitor.changes.extend(detected_changes)
                            
                            # Keep only last 50 changes to prevent memory issues
                            if len(monitor.changes) > 50:
                                monitor.changes = monitor.changes[-50:]
                        else:
                            logger.info(f"Job {job_id}: No changes detected")
                        
                        # Update current content
                        monitor.previous_content = monitor.current_content
                        monitor.current_content = new_content
                    
                    # Save job status
                    self.save_jobs()
                    
                    # Wait for next check
                    wait_time = job.check_interval_minutes * 60
                    if stop_event.wait(wait_time):
                        break
                        
                except Exception as e:
                    logger.error(f"Error in monitoring loop for job {job_id}: {e}")
                    job.error_message = str(e)
                    self.save_jobs()
                    time.sleep(60)  # Wait before retrying
                    
        except Exception as e:
            job.status = 'error'
            job.error_message = str(e)
            logger.error(f"Fatal error in job {job_id}: {e}")
        finally:
            job.status = 'stopped'
            self.save_jobs()
            # Cleanup
            if job_id in self.monitors:
                if self.monitors[job_id].driver:
                    self.monitors[job_id].driver.quit()
                del self.monitors[job_id]
    
    def _save_results(self, job_id: str, changes: List[dict]):
        """Save detection results to file"""
        try:
            results_file = os.path.join(self.results_dir, f"{job_id}.json")
            
            # Load existing results
            existing_results = []
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    existing_results = json.load(f)
            
            # Add new changes
            for change in changes:
                change['detected_at'] = datetime.now().isoformat()
                existing_results.append(change)
            
            # Keep only last 200 results
            if len(existing_results) > 200:
                existing_results = existing_results[-200:]
            
            # Save results
            with open(results_file, 'w') as f:
                json.dump(existing_results, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving results for job {job_id}: {e}")
    
    def stop_job(self, job_id: str) -> bool:
        """Stop monitoring for a specific job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # Signal stop event
        if job_id in self.stop_events:
            self.stop_events[job_id].set()
        
        # Wait for thread to finish
        if job_id in self.monitor_threads:
            thread = self.monitor_threads[job_id]
            thread.join(timeout=5)
            del self.monitor_threads[job_id]
        
        # Cleanup monitor
        if job_id in self.monitors:
            if self.monitors[job_id].driver:
                self.monitors[job_id].driver.quit()
            del self.monitors[job_id]
        
        # Cleanup stop event
        if job_id in self.stop_events:
            del self.stop_events[job_id]
        
        job.status = 'stopped'
        self.save_jobs()
        
        logger.info(f"Stopped job {job_id}")
        return True
    
    def pause_job(self, job_id: str) -> bool:
        """Pause monitoring for a specific job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status != 'running':
            return False
        
        # Signal stop event (will pause the job)
        if job_id in self.stop_events:
            self.stop_events[job_id].set()
        
        job.status = 'paused'
        self.save_jobs()
        
        logger.info(f"Paused job {job_id}")
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its results"""
        if job_id not in self.jobs:
            return False
        
        # Stop the job first
        self.stop_job(job_id)
        
        # Delete results file
        results_file = os.path.join(self.results_dir, f"{job_id}.json")
        if os.path.exists(results_file):
            os.remove(results_file)
        
        # Remove job
        del self.jobs[job_id]
        self.save_jobs()
        
        logger.info(f"Deleted job {job_id}")
        return True
    
    def get_job(self, job_id: str) -> Optional[MonitoringJob]:
        """Get job details"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[MonitoringJob]:
        """Get all jobs"""
        return list(self.jobs.values())
    
    def get_job_results(self, job_id: str, limit: int = 50) -> List[dict]:
        """Get results for a specific job"""
        try:
            results_file = os.path.join(self.results_dir, f"{job_id}.json")
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results = json.load(f)
                return results[-limit:] if limit else results
            return []
        except Exception as e:
            logger.error(f"Error loading results for job {job_id}: {e}")
            return []
    
    def get_job_stats(self, job_id: str) -> dict:
        """Get statistics for a job"""
        if job_id not in self.jobs:
            return {}
        
        job = self.jobs[job_id]
        results = self.get_job_results(job_id)
        
        # Calculate statistics
        stats = {
            'total_checks': job.total_checks,
            'total_changes': len(results),
            'changes_detected': job.changes_detected,
            'last_check': job.last_check,
            'status': job.status,
            'created_at': job.created_at,
            'error_message': job.error_message
        }
        
        # Calculate change types
        change_types = {}
        for result in results:
            change_type = result.get('type', 'unknown')
            change_types[change_type] = change_types.get(change_type, 0) + 1
        
        stats['change_types'] = change_types
        
        # Calculate AI detections if available
        ai_detections = 0
        companies_detected = []
        for result in results:
            if result.get('ai_analysis', {}).get('new_companies_detected'):
                ai_detections += 1
                companies = result.get('ai_analysis', {}).get('companies', [])
                for company in companies:
                    if company.get('name') not in companies_detected:
                        companies_detected.append(company.get('name'))
        
        stats['ai_detections'] = ai_detections
        stats['companies_detected'] = companies_detected
        
        return stats

# Initialize Flask app, user manager, and job manager

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Generate a secure secret key
# Enable CORS for all routes and origins
CORS(app, supports_credentials=True)
user_manager = UserManager()
job_manager = JobManager()
API_KEY = os.getenv('API_KEY')  # Load from environment

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = user_manager.get_user(session['user_id'])
        if not user or not user.is_active:
            session.pop('user_id', None)
            return jsonify({'error': 'Invalid session'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        # Basic validation
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Create user
        user_id = user_manager.create_user(email, password)
        if not user_id:
            return jsonify({'error': 'Email already exists'}), 409
        
        # Auto-login after registration
        session['user_id'] = user_id
        user = user_manager.get_user(user_id)
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'created_at': user.created_at
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        # Authenticate user
        user = user_manager.authenticate_user(email, password)
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Set session
        session['user_id'] = user.user_id
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'last_login': user.last_login
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user"""
    try:
        session.pop('user_id', None)
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile"""
    try:
        user = user_manager.get_user(session['user_id'])
        user_jobs = job_manager.get_user_jobs(user.user_id)
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'total_jobs': len(user_jobs),
                'running_jobs': len([j for j in user_jobs if j.status == 'running']),
                'total_changes': sum(j.changes_detected for j in user_jobs)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Job management routes (now with authentication)
@app.route('/api/jobs', methods=['POST'])
@require_auth
def create_job():
    """Create a new monitoring job"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not all(k in data for k in ['name', 'url', 'check_interval_minutes']):
            return jsonify({
                'error': 'Missing required fields: name, url, check_interval_minutes'
            }), 400
        
        name = data['name']
        url = data['url']
        check_interval = int(data['check_interval_minutes'])
        
        if check_interval < 1:
            return jsonify({'error': 'check_interval_minutes must be at least 1'}), 400
        
        # Create job for authenticated user
        job_id = job_manager.create_job(session['user_id'], name, url, check_interval)
        job = job_manager.get_job(job_id)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job': asdict(job),
            'message': f'Job "{name}" created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
@require_auth
def get_user_jobs():
    """Get all monitoring jobs for authenticated user"""
    try:
        jobs = job_manager.get_user_jobs(session['user_id'])
        return jsonify({
            'success': True,
            'jobs': [asdict(job) for job in jobs],
            'total': len(jobs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """Get specific job details"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/start', methods=['POST'])
@require_auth
def start_job(job_id):
    """Start monitoring for a specific job"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        # Get API key from request or use default
        data = request.get_json() or {}
        api_key = data.get('api_key', API_KEY)
        
        success = job_manager.start_job(job_id, api_key)
        if not success:
            return jsonify({'error': 'Failed to start job'}), 400
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'message': f'Job "{job.name}" started successfully',
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/stop', methods=['POST'])
@require_auth
def stop_job(job_id):
    """Stop monitoring for a specific job"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        success = job_manager.stop_job(job_id)
        if not success:
            return jsonify({'error': 'Failed to stop job'}), 400
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'message': f'Job "{job.name}" stopped successfully',
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/pause', methods=['POST'])
@require_auth
def pause_job(job_id):
    """Pause monitoring for a specific job"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        success = job_manager.pause_job(job_id)
        if not success:
            return jsonify({'error': 'Job not found or not running'}), 400
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'message': f'Job "{job.name}" paused successfully',
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
@require_auth
def delete_job(job_id):
    """Delete a job and its results"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        job = job_manager.get_job(job_id)
        job_name = job.name
        success = job_manager.delete_job(job_id)
        
        return jsonify({
            'success': True,
            'message': f'Job "{job_name}" deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/results', methods=['GET'])
@require_auth
def get_job_results(job_id):
    """Get results for a specific job"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        job = job_manager.get_job(job_id)
        
        # Get limit from query parameters
        limit = request.args.get('limit', 50, type=int)
        
        results = job_manager.get_job_results(job_id, limit)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_name': job.name,
            'results': results,
            'total_results': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/stats', methods=['GET'])
@require_auth
def get_job_stats(job_id):
    """Get statistics for a specific job"""
    try:
        if not job_manager.user_owns_job(session['user_id'], job_id):
            return jsonify({'error': 'Job not found or access denied'}), 404
        
        job = job_manager.get_job(job_id)
        stats = job_manager.get_job_stats(job_id)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_name': job.name,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
@require_auth
def get_user_status():
    """Get user-specific system status"""
    try:
        user_jobs = job_manager.get_user_jobs(session['user_id'])
        
        status = {
            'total_jobs': len(user_jobs),
            'running_jobs': len([j for j in user_jobs if j.status == 'running']),
            'paused_jobs': len([j for j in user_jobs if j.status == 'paused']),
            'stopped_jobs': len([j for j in user_jobs if j.status == 'stopped']),
            'error_jobs': len([j for j in user_jobs if j.status == 'error']),
            'total_changes_detected': sum(j.changes_detected for j in user_jobs),
            'ai_enabled': API_KEY is not None,
            'system_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Web Change Monitor API is running',
        'timestamp': datetime.now().isoformat(),
        'authentication': 'enabled',
        'total_users': len(user_manager.users),
        'total_jobs': len(job_manager.jobs)
    })

# Admin routes (optional - for system monitoring)
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get overall system statistics (no auth required for basic stats)"""
    try:
        all_jobs = job_manager.get_all_jobs()
        
        stats = {
            'system': {
                'total_users': len(user_manager.users),
                'active_users': len([u for u in user_manager.users.values() if u.is_active]),
                'total_jobs': len(all_jobs),
                'running_jobs': len([j for j in all_jobs if j.status == 'running']),
                'total_changes': sum(j.changes_detected for j in all_jobs),
            },
            'ai_enabled': API_KEY is not None,
            'uptime': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🔐 Web Change Monitor API with Authentication")
    print("=============================================")
    print("🔧 Features:")
    print("  - User registration & authentication")
    print("  - SHA-256 password hashing")
    print("  - Session-based authentication")
    print("  - User-specific job isolation")
    print("  - Create monitoring jobs with custom intervals")
    print("  - Start/stop/pause job management")
    print("  - AI-powered change analysis")
    print("  - Results storage and retrieval")
    print("  - RESTful API for all operations")
    print("")
    print("🔐 Authentication Endpoints:")
    print("  POST   /api/auth/register        - Register new user")
    print("  POST   /api/auth/login           - Login user")
    print("  POST   /api/auth/logout          - Logout user")
    print("  GET    /api/auth/profile         - Get user profile")
    print("")
    print("📡 Job Management Endpoints (Auth Required):")
    print("  POST   /api/jobs                 - Create new job")
    print("  GET    /api/jobs                 - Get user's jobs")
    print("  GET    /api/jobs/<id>            - Get job details")
    print("  POST   /api/jobs/<id>/start      - Start job")
    print("  POST   /api/jobs/<id>/stop       - Stop job")
    print("  POST   /api/jobs/<id>/pause      - Pause job")
    print("  DELETE /api/jobs/<id>            - Delete job")
    print("  GET    /api/jobs/<id>/results    - Get job results")
    print("  GET    /api/jobs/<id>/stats      - Get job statistics")
    print("  GET    /api/status               - User status")
    print("")
    print("🌐 Public Endpoints:")
    print("  GET    /api/health               - Health check")
    print("  GET    /api/admin/stats          - System statistics")
    print("")
    print("🔑 Usage:")
    print("  1. Register: curl -X POST http://localhost:5000/api/auth/register \\")
    print("                    -H 'Content-Type: application/json' \\")
    print("                    -d '{\"email\":\"user@example.com\",\"password\":\"password123\"}'")
    print("")
    print("  2. Login: curl -X POST http://localhost:5000/api/auth/login \\")
    print("                 -H 'Content-Type: application/json' \\")
    print("                 -d '{\"email\":\"user@example.com\",\"password\":\"password123\"}' \\")
    print("                 -c cookies.txt")
    print("")
    print("  3. Create Job: curl -X POST http://localhost:5000/api/jobs \\")
    print("                      -H 'Content-Type: application/json' \\")
    print("                      -b cookies.txt \\")
    print("                      -d '{\"name\":\"My Website\",\"url\":\"https://example.com\",\"check_interval_minutes\":5}'")
    print("")
    print(f"🤖 AI Analysis: {'Enabled' if API_KEY else 'Disabled (set API_KEY environment variable)'}")
    print(f"💾 Data Storage:")
    print(f"   - Users: users.json")
    print(f"   - Jobs: jobs.json") 
    print(f"   - Results: results/ directory")
    print("")
    print("🚀 Starting server on http://localhost:5000")
    print("   Test with: curl http://localhost:5000/api/health")
    print("   Press Ctrl+C to stop")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        # Stop all running jobs
        for job_id in list(job_manager.jobs.keys()):
            if job_manager.jobs[job_id].status == 'running':
                job_manager.stop_job(job_id)
        print("✅ All jobs stopped. Goodbye!")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        print(f"❌ Server failed to start: {e}")
        print("💡 Make sure port 5000 is available and webmonitor.py exists")