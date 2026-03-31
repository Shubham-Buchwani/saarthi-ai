import requests

try:
    resp = requests.options(
        "http://127.0.0.1:8000/api/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    )
    print("Status:", resp.status_code)
    print("Headers:", resp.headers)
except Exception as e:
    print("Exception:", e)
