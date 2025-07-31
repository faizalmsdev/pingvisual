from flask import Flask, request, jsonify
import json
import os
import uuid
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import logging

# Import the existing WebChangeMonitor class
from webmonitor import WebChangeMonitor, AIAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MonitoringJob:
    job_id: str
    name: str
    url: str
    check_interval_minutes: int
    created_at: str
    status: str  # 'created', 'running', 'paused', 'stopped', 'error'
    last_check: Optional[str] = None
    total_checks: int = 0
    changes_detected: int = 0
    error_message: Optional[str] = None

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
    
    def create_job(self, name: str, url: str, check_interval_minutes: int) -> str:
        """Create a new monitoring job"""
        job_id = str(uuid.uuid4())
        job = MonitoringJob(
            job_id=job_id,
            name=name,
            url=url,
            check_interval_minutes=check_interval_minutes,
            created_at=datetime.now().isoformat(),
            status='created'
        )
        self.jobs[job_id] = job
        self.save_jobs()
        logger.info(f"Created job {job_id}: {name}")
        return job_id
    
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

# Initialize Flask app and job manager
app = Flask(__name__)
job_manager = JobManager()
API_KEY = os.getenv('API_KEY')  # Load from environment

@app.route('/api/jobs', methods=['POST'])
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
        
        # Create job
        job_id = job_manager.create_job(name, url, check_interval)
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
def get_all_jobs():
    """Get all monitoring jobs"""
    try:
        jobs = job_manager.get_all_jobs()
        return jsonify({
            'success': True,
            'jobs': [asdict(job) for job in jobs],
            'total': len(jobs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get specific job details"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/start', methods=['POST'])
def start_job(job_id):
    """Start monitoring for a specific job"""
    try:
        # Get API key from request or use default
        data = request.get_json() or {}
        api_key = data.get('api_key', API_KEY)
        
        success = job_manager.start_job(job_id, api_key)
        if not success:
            return jsonify({'error': 'Failed to start job or job not found'}), 400
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'message': f'Job "{job.name}" started successfully',
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/stop', methods=['POST'])
def stop_job(job_id):
    """Stop monitoring for a specific job"""
    try:
        success = job_manager.stop_job(job_id)
        if not success:
            return jsonify({'error': 'Job not found'}), 404
        
        job = job_manager.get_job(job_id)
        return jsonify({
            'success': True,
            'message': f'Job "{job.name}" stopped successfully',
            'job': asdict(job)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """Pause monitoring for a specific job"""
    try:
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
def delete_job(job_id):
    """Delete a job and its results"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        job_name = job.name
        success = job_manager.delete_job(job_id)
        
        return jsonify({
            'success': True,
            'message': f'Job "{job_name}" deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/results', methods=['GET'])
def get_job_results(job_id):
    """Get results for a specific job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
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
def get_job_stats(job_id):
    """Get statistics for a specific job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
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
def get_system_status():
    """Get overall system status"""
    try:
        jobs = job_manager.get_all_jobs()
        
        status = {
            'total_jobs': len(jobs),
            'running_jobs': len([j for j in jobs if j.status == 'running']),
            'paused_jobs': len([j for j in jobs if j.status == 'paused']),
            'stopped_jobs': len([j for j in jobs if j.status == 'stopped']),
            'error_jobs': len([j for j in jobs if j.status == 'error']),
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
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("Web Change Monitor API")
    print("=====================")
    print("🔧 Features:")
    print("  - Create monitoring jobs with custom intervals")
    print("  - Start/stop/pause job management")
    print("  - AI-powered change analysis")
    print("  - Results storage and retrieval")
    print("  - RESTful API for all operations")
    print("")
    print("📡 API Endpoints:")
    print("  POST   /api/jobs                 - Create new job")
    print("  GET    /api/jobs                 - Get all jobs")
    print("  GET    /api/jobs/<id>            - Get job details")
    print("  POST   /api/jobs/<id>/start      - Start job")
    print("  POST   /api/jobs/<id>/stop       - Stop job")
    print("  POST   /api/jobs/<id>/pause      - Pause job")
    print("  DELETE /api/jobs/<id>            - Delete job")
    print("  GET    /api/jobs/<id>/results    - Get job results")
    print("  GET    /api/jobs/<id>/stats      - Get job statistics")
    print("  GET    /api/status               - System status")
    print("  GET    /api/health               - Health check")
    print("")
    print(f"🤖 AI Analysis: {'Enabled' if API_KEY else 'Disabled (set API_KEY environment variable)'}")
    print("")
    print("🚀 Starting server on http://localhost:8000")
    print("   Test with: curl http://localhost:8000/api/health")
    print("   Press Ctrl+C to stop")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8000, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        # Stop all running jobs
        for job_id in list(job_manager.jobs.keys()):
            if job_manager.jobs[job_id].status == 'running':
                job_manager.stop_job(job_id)
        print("✅ All jobs stopped. Goodbye!")