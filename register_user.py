import requests
import json

def register_user(email, password, base_url="http://localhost:5000"):
    """Register a new user"""
    try:
        register_url = f"{base_url}/api/auth/register"
        register_data = {
            "email": email,
            "password": password
        }
        
        print(f"🔐 Registering user with email: {email}")
        response = requests.post(register_url, json=register_data)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ User registered successfully!")
            print(f"   User ID: {data['user']['user_id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Token: {data['token']}")
            return True
        elif response.status_code == 409:
            print(f"ℹ️  User already exists, trying to login...")
            return login_user(email, password, base_url)
        else:
            print(f"❌ Registration failed: {response.json().get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

def login_user(email, password, base_url="http://localhost:5000"):
    """Login user"""
    try:
        login_url = f"{base_url}/api/auth/login"
        login_data = {
            "email": email,
            "password": password
        }
        
        print(f"🔐 Logging in with email: {email}")
        response = requests.post(login_url, json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"   User ID: {data['user']['user_id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Token: {data['token']}")
            return True
        else:
            print(f"❌ Login failed: {response.json().get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def main():
    EMAIL = "faizalmohamed5302002@gmail.com"
    PASSWORD = "Faizal@123"
    
    print("🔧 User Registration/Login Test")
    print("=" * 40)
    
    # Try to register (will try login if user exists)
    success = register_user(EMAIL, PASSWORD)
    
    if success:
        print("\n✅ Ready to create jobs!")
    else:
        print("\n❌ Authentication failed")

if __name__ == "__main__":
    main()
