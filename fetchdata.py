import requests

url = "http://209.74.95.163:5000/api/changes/latest"  # Change this to your desired URL

response = requests.get(url)
if response.status_code == 200:
    print("Success!")
    print(response.json())
else:
    print(f"Failed with status code: {response.status_code}")
    print(response.text)