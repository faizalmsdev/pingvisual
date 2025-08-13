import requests
import json

def register_new_user(email, password, base_url="http://localhost:5000"):
    """Register a new user"""
    try:
        register_url = f"{base_url}/api/auth/register"
        register_data = {
            "email": email,
            "password": password
        }
        
        print(f"🔐 Registering new user with email: {email}")
        response = requests.post(register_url, json=register_data)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ User registered successfully!")
            print(f"   User ID: {data['user']['user_id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Token: {data['token']}")
            print(f"   Created at: {data['user']['created_at']}")
            return data['token'], data['user']['user_id']
        elif response.status_code == 409:
            print(f"❌ User already exists with email: {email}")
            return None, None
        else:
            print(f"❌ Registration failed: {response.json().get('error', 'Unknown error')}")
            return None, None
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None, None

def main():
    EMAIL = "faizalmohamed.vi@gmail.com"
    PASSWORD = "Faizal@123"
    
    print("🔧 New User Registration")
    print("=" * 40)
    
    # Register new user
    token, user_id = register_new_user(EMAIL, PASSWORD)
    
    if token and user_id:
        print(f"\n✅ New user successfully created!")
        print(f"📋 Login Credentials:")
        print(f"   Email: {EMAIL}")
        print(f"   Password: {PASSWORD}")
        print(f"   User ID: {user_id}")
        print(f"   Token: {token}")
        print(f"\n🚀 Ready to create jobs with this account!")
    else:
        print(f"\n❌ Failed to create new user")

if __name__ == "__main__":
    main()
