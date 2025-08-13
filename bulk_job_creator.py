import pandas as pd
import requests
import json
import time
from typing import Optional

class JobCreator:
    def __init__(self, base_url: str = "http://localhost:5000"):
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
                print(f"   Email: {data['user']['email']}")
                return True
            else:
                print(f"❌ Login failed: {response.json().get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def create_job(self, name: str, url: str, check_interval_minutes: int) -> Optional[str]:
        """Create a monitoring job"""
        try:
            jobs_url = f"{self.base_url}/api/jobs"
            job_data = {
                "name": name,
                "url": url,
                "check_interval_minutes": check_interval_minutes
            }
            
            # Add authentication header
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            print(f"📝 Creating job: {name}")
            print(f"   URL: {url}")
            print(f"   Interval: {check_interval_minutes} minutes ({check_interval_minutes/60:.1f} hours)")
            
            response = self.session.post(jobs_url, json=job_data, headers=headers)
            
            if response.status_code == 201:
                data = response.json()
                job_id = data['job_id']
                print(f"✅ Job created successfully!")
                print(f"   Job ID: {job_id}")
                return job_id
            else:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"❌ Failed to create job: {error_msg}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating job: {e}")
            return None
    
    def load_jobs_from_excel(self, excel_file: str) -> list:
        """Load job data from Excel file"""
        try:
            print(f"📊 Reading Excel file: {excel_file}")
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            print(f"📋 Excel file loaded successfully!")
            print(f"   Total rows: {len(df)}")
            print(f"   Columns: {list(df.columns)}")
            
            # Display first few rows for verification
            print("\n📑 First few rows:")
            print(df.head())
            
            # Extract job data (skip header row, start from index 1)
            jobs = []
            for index, row in df.iterrows():
                # Skip header row (index 0)
                if index == 0:
                    continue
                    
                # Get URL from first column and job name from second column
                url = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                job_name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else f"Job {index}"
                
                # Skip empty URLs
                if not url or url.lower() in ['nan', 'none', '']:
                    print(f"⚠️  Skipping row {index + 1}: Empty URL")
                    continue
                
                # Add http:// if no protocol specified
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                jobs.append({
                    'name': job_name,
                    'url': url,
                    'row': index + 1
                })
            
            print(f"\n✅ Loaded {len(jobs)} valid jobs from Excel file")
            return jobs
            
        except Exception as e:
            print(f"❌ Error reading Excel file: {e}")
            return []
    
    def create_jobs_from_excel(self, excel_file: str, check_interval_hours: int = 8):
        """Create jobs from Excel file"""
        # Convert hours to minutes
        check_interval_minutes = check_interval_hours * 60
        
        print(f"🚀 Starting job creation process")
        print(f"   Excel file: {excel_file}")
        print(f"   Check interval: {check_interval_hours} hours ({check_interval_minutes} minutes)")
        print("=" * 60)
        
        # Load jobs from Excel
        jobs = self.load_jobs_from_excel(excel_file)
        
        if not jobs:
            print("❌ No jobs to create")
            return
        
        # Create each job
        created_jobs = []
        failed_jobs = []
        
        for i, job in enumerate(jobs, 1):
            print(f"\n🔄 Processing job {i}/{len(jobs)} (Row {job['row']})")
            
            job_id = self.create_job(
                name=job['name'],
                url=job['url'],
                check_interval_minutes=check_interval_minutes
            )
            
            if job_id:
                created_jobs.append({**job, 'job_id': job_id})
            else:
                failed_jobs.append(job)
            
            # Small delay between requests
            time.sleep(1)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 JOB CREATION SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully created: {len(created_jobs)} jobs")
        print(f"❌ Failed to create: {len(failed_jobs)} jobs")
        
        if created_jobs:
            print("\n✅ CREATED JOBS:")
            for job in created_jobs:
                print(f"   • {job['name']} - {job['url']} (ID: {job['job_id']})")
        
        if failed_jobs:
            print("\n❌ FAILED JOBS:")
            for job in failed_jobs:
                print(f"   • {job['name']} - {job['url']} (Row: {job['row']})")
        
        print(f"\n🎯 Total jobs processed: {len(jobs)}")
        print(f"🎉 Success rate: {len(created_jobs)/len(jobs)*100:.1f}%")

def main():
    """Main function to run the job creator"""
    print("🔧 Web Change Monitor - Bulk Job Creator")
    print("=" * 50)
    
    # Configuration
    EMAIL = "faizalmohamed5302002@gmail.com"
    PASSWORD = "Faizal@123"
    EXCEL_FILE = "job-settings.xlsx"
    CHECK_INTERVAL_HOURS = 8  # Check every 8 hours
    
    # Create job creator instance
    creator = JobCreator()
    
    # Login
    if not creator.login(EMAIL, PASSWORD):
        print("❌ Cannot proceed without login. Exiting...")
        return
    
    # Create jobs from Excel
    creator.create_jobs_from_excel(EXCEL_FILE, CHECK_INTERVAL_HOURS)

if __name__ == "__main__":
    main()
