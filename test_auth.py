#!/usr/bin/env python3
"""
Test script demonstrating different authentication methods for the Web Monitor API
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_authentication_methods():
    print("🔐 Testing Web Monitor API Authentication Methods")
    print("=" * 50)
    
    # Test data
    email = "test@example.com"
    password = "testpass123"
    
    # 1. Register a test user
    print("\n1. Registering test user...")
    register_data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    if response.status_code == 201:
        data = response.json()
        user_id = data['token']  # The user_id is returned as token
        print(f"✅ User registered successfully!")
        print(f"   User ID (Token): {user_id}")
    else:
        print(f"❌ Registration failed: {response.text}")
        return
    
    # 2. Test session-based authentication (cookies)
    print("\n2. Testing Session Authentication (Cookies)...")
    session = requests.Session()
    login_response = session.post(f"{BASE_URL}/api/auth/login", json=register_data)
    
    if login_response.status_code == 200:
        print("✅ Login successful with session")
        # Test API call with session
        jobs_response = session.get(f"{BASE_URL}/api/jobs")
        print(f"   Jobs API call: {jobs_response.status_code} - {jobs_response.json()['success']}")
    else:
        print(f"❌ Login failed: {login_response.text}")
    
    # 3. Test Bearer token authentication
    print("\n3. Testing Bearer Token Authentication...")
    headers = {
        "Authorization": f"Bearer {user_id}",
        "Content-Type": "application/json"
    }
    
    jobs_response = requests.get(f"{BASE_URL}/api/jobs", headers=headers)
    if jobs_response.status_code == 200:
        print("✅ Bearer token authentication successful")
        print(f"   Jobs API call: {jobs_response.status_code} - {jobs_response.json()['success']}")
    else:
        print(f"❌ Bearer token auth failed: {jobs_response.text}")
    
    # 4. Test X-User-Token header authentication
    print("\n4. Testing X-User-Token Header Authentication...")
    headers = {
        "X-User-Token": user_id,
        "Content-Type": "application/json"
    }
    
    jobs_response = requests.get(f"{BASE_URL}/api/jobs", headers=headers)
    if jobs_response.status_code == 200:
        print("✅ X-User-Token authentication successful")
        print(f"   Jobs API call: {jobs_response.status_code} - {jobs_response.json()['success']}")
    else:
        print(f"❌ X-User-Token auth failed: {jobs_response.text}")
    
    # 5. Test query parameter authentication
    print("\n5. Testing Query Parameter Authentication...")
    
    jobs_response = requests.get(f"{BASE_URL}/api/jobs?token={user_id}")
    if jobs_response.status_code == 200:
        print("✅ Query parameter authentication successful")
        print(f"   Jobs API call: {jobs_response.status_code} - {jobs_response.json()['success']}")
    else:
        print(f"❌ Query parameter auth failed: {jobs_response.text}")
    
    # 6. Test creating a job with token authentication
    print("\n6. Testing Job Creation with Bearer Token...")
    headers = {
        "Authorization": f"Bearer {user_id}",
        "Content-Type": "application/json"
    }
    
    job_data = {
        "name": "Test Website Monitor",
        "url": "https://httpbin.org/html",
        "check_interval_minutes": 5
    }
    
    create_response = requests.post(f"{BASE_URL}/api/jobs", json=job_data, headers=headers)
    if create_response.status_code == 201:
        job_info = create_response.json()
        job_id = job_info['job_id']
        print("✅ Job created successfully with token auth")
        print(f"   Job ID: {job_id}")
        print(f"   Job Name: {job_info['job']['name']}")
        
        # Test getting job details
        job_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}", headers=headers)
        if job_response.status_code == 200:
            print("✅ Job details retrieved successfully")
        
    else:
        print(f"❌ Job creation failed: {create_response.text}")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication testing complete!")
    print("\n💡 Summary of Authentication Methods:")
    print("   1. Session cookies (traditional web app)")
    print("   2. Bearer token in Authorization header")
    print("   3. Custom X-User-Token header")
    print("   4. Token as query parameter")
    print(f"\n🔑 Your User Token: {user_id}")
    print("   Use this token for API access without sessions")

if __name__ == "__main__":
    try:
        # Check if API is running
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health_response.status_code == 200:
            test_authentication_methods()
        else:
            print("❌ API is not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")
