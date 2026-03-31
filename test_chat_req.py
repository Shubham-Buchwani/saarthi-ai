import requests

try:
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"message": "Hello", "session_id": ""},
        headers={"Authorization": "Bearer TEST_TOKEN"}
    )
    print("Status:", resp.status_code)
    print("Body:", resp.text)
except Exception as e:
    print("Exception:", e)
