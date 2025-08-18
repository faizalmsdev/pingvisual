import requests
import json
import time
from typing import List, Dict

class BulkJobStarter:
    def __init__(self, base_url: str = "http://209.74.95.163:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        
    def login(self, email: str, password: str) -> bool:
        """Login to the API and get authentication token"""
        try:
            login_url = f"{self.base_url}/api/auth/login"
            login_data = {
                "email": email,
                "password": password
            }
            
            print(f"🔐 Logging in with email: {email}")
            response = self.session.post(login_url, json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data['token']
                self.user_id = data['user']['user_id']
                print(f"✅ Login successful!")
                print(f"   User ID: {self.user_id}")
                return True
            else:
                print(f"❌ Login failed: {response.json().get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs for the authenticated user"""
        try:
            jobs_url = f"{self.base_url}/api/jobs"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            print(f"📋 Fetching all jobs...")
            response = self.session.get(jobs_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                jobs = data['jobs']
                print(f"✅ Found {len(jobs)} jobs")
                return jobs
            else:
                print(f"❌ Failed to fetch jobs: {response.json().get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching jobs: {e}")
            return []
    
    def start_job(self, job_id: str, job_name: str) -> bool:
        """Start a specific job"""
        try:
            start_url = f"{self.base_url}/api/jobs/{job_id}/start"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Include API key if available (optional)
            data = {}
            
            response = self.session.post(start_url, json=data, headers=headers)
            
            if response.status_code == 200:
                return True
            else:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"   ❌ Failed: {error_msg}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def start_all_jobs(self, delay_between_starts: float = 0.5):
        """Start all jobs for the authenticated user"""
        print(f"🚀 Starting bulk job activation process")
        print("=" * 60)
        
        # Get all jobs
        jobs = self.get_all_jobs()
        
        if not jobs:
            print("❌ No jobs found to start")
            return
        
        # Filter jobs that are not already running
        jobs_to_start = [job for job in jobs if job['status'] != 'running']
        already_running = [job for job in jobs if job['status'] == 'running']
        
        print(f"\n📊 Job Status Summary:")
        print(f"   Total jobs: {len(jobs)}")
        print(f"   Already running: {len(already_running)}")
        print(f"   To be started: {len(jobs_to_start)}")
        
        if already_running:
            print(f"\n⚡ Already running jobs:")
            for job in already_running[:5]:  # Show first 5
                print(f"   • {job['name']} (ID: {job['job_id']})")
            if len(already_running) > 5:
                print(f"   ... and {len(already_running) - 5} more")
        
        if not jobs_to_start:
            print(f"\n✅ All jobs are already running!")
            return
        
        # Confirm before starting
        print(f"\n❓ Ready to start {len(jobs_to_start)} jobs. Continue? (y/n): ", end="")
        confirm = input().lower().strip()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return
        
        # Start each job
        started_jobs = []
        failed_jobs = []
        
        print(f"\n🔄 Starting jobs...")
        print("-" * 60)
        
        for i, job in enumerate(jobs_to_start, 1):
            job_id = job['job_id']
            job_name = job['name']
            
            print(f"🔄 Starting job {i}/{len(jobs_to_start)}: {job_name[:50]}{'...' if len(job_name) > 50 else ''}")
            
            success = self.start_job(job_id, job_name)
            
            if success:
                started_jobs.append(job)
                print(f"   ✅ Started successfully")
            else:
                failed_jobs.append(job)
            
            # Small delay between requests to avoid overwhelming the server
            if i < len(jobs_to_start):
                time.sleep(delay_between_starts)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 BULK JOB START SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully started: {len(started_jobs)} jobs")
        print(f"❌ Failed to start: {len(failed_jobs)} jobs")
        print(f"⚡ Already running: {len(already_running)} jobs")
        
        if failed_jobs:
            print(f"\n❌ FAILED TO START:")
            for job in failed_jobs[:10]:  # Show first 10 failed
                print(f"   • {job['name']} (ID: {job['job_id']})")
            if len(failed_jobs) > 10:
                print(f"   ... and {len(failed_jobs) - 10} more")
        
        total_running = len(started_jobs) + len(already_running)
        print(f"\n🎯 Total jobs now running: {total_running}/{len(jobs)}")
        print(f"🎉 Success rate: {len(started_jobs)/(len(jobs_to_start) if jobs_to_start else 1)*100:.1f}%")
        
        if started_jobs:
            print(f"\n🚀 All started jobs will now monitor their respective URLs every 8 hours!")
            print(f"📊 You can check job status and results through the API endpoints.")

    def stop_job(self, job_id: str, job_name: str) -> bool:
        """Stop a specific job"""
        try:
            stop_url = f"{self.base_url}/api/jobs/{job_id}/stop"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.session.post(stop_url, headers=headers)
            if response.status_code == 200:
                return True
            else:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"   ❌ Failed to stop: {error_msg}")
                return False
        except Exception as e:
            print(f"   ❌ Error stopping job: {e}")
            return False

    def stop_all_jobs(self, delay_between_stops: float = 0.5):
        """Stop all running jobs for the authenticated user"""
        print(f"🛑 Stopping all running jobs...")
        print("=" * 60)
        jobs = self.get_all_jobs()
        if not jobs:
            print("❌ No jobs found to stop")
            return
        jobs_to_stop = [job for job in jobs if job['status'] == 'running']
        not_running = [job for job in jobs if job['status'] != 'running']
        print(f"\n📊 Job Status Summary:")
        print(f"   Total jobs: {len(jobs)}")
        print(f"   Running: {len(jobs_to_stop)}")
        print(f"   Not running: {len(not_running)}")
        if not jobs_to_stop:
            print(f"\n✅ No jobs are running!")
            return
        print(f"\n❓ Ready to stop {len(jobs_to_stop)} jobs. Continue? (y/n): ", end="")
        confirm = input().lower().strip()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return
        stopped_jobs = []
        failed_jobs = []
        print(f"\n🔄 Stopping jobs...")
        print("-" * 60)
        for i, job in enumerate(jobs_to_stop, 1):
            job_id = job['job_id']
            job_name = job['name']
            print(f"🔄 Stopping job {i}/{len(jobs_to_stop)}: {job_name[:50]}{'...' if len(job_name) > 50 else ''}")
            success = self.stop_job(job_id, job_name)
            if success:
                stopped_jobs.append(job)
                print(f"   ✅ Stopped successfully")
            else:
                failed_jobs.append(job)
            if i < len(jobs_to_stop):
                time.sleep(delay_between_stops)
        print("\n" + "=" * 60)
        print("📊 BULK JOB STOP SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully stopped: {len(stopped_jobs)} jobs")
        print(f"❌ Failed to stop: {len(failed_jobs)} jobs")
        print(f"⚡ Not running: {len(not_running)} jobs")
        if failed_jobs:
            print(f"\n❌ FAILED TO STOP:")
            for job in failed_jobs[:10]:
                print(f"   • {job['name']} (ID: {job['job_id']})")
            if len(failed_jobs) > 10:
                print(f"   ... and {len(failed_jobs) - 10} more")
        total_not_running = len(stopped_jobs) + len(not_running)
        print(f"\n🎯 Total jobs now not running: {total_not_running}/{len(jobs)}")
        print(f"🎉 Success rate: {len(stopped_jobs)/(len(jobs_to_stop) if jobs_to_stop else 1)*100:.1f}%")
        if stopped_jobs:
            print(f"\n🛑 All stopped jobs will no longer monitor their URLs until started again!")
            print(f"📊 You can check job status and results through the API endpoints.")

def main():
    """Main function to run the bulk job starter"""
    print("🚀 Web Change Monitor - Bulk Job Starter")
    print("=" * 50)
    
    # Configuration
    EMAIL = "faizalmohamed.vi@gmail.com"
    PASSWORD = "Faizal@123"
    
    # Create job starter instance
    starter = BulkJobStarter()
    
    # Login
    if not starter.login(EMAIL, PASSWORD):
        print("❌ Cannot proceed without login. Exiting...")
        return
    
    print("\nWhat do you want to do?")
    print("1. Start all jobs")
    print("2. Stop all jobs")
    print("3. Stop all jobs, then start all jobs")
    action = input("Enter choice (1-3): ").strip()
    if action == "1":
        starter.start_all_jobs()
    elif action == "2":
        starter.stop_all_jobs()
    elif action == "3":
        starter.stop_all_jobs()
        print("\nWaiting 5 seconds before starting all jobs again...")
        time.sleep(5)
        starter.start_all_jobs()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
