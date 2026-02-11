import requests
import json

base_url = "http://localhost:8000"
session_id = "test_sess_mapping"

messages = [
    {"role": "user", "content": "Hi, I'm Sarah and I want to buy an office space in West Cairo for my own business. My number is 555-0199."},
    {"role": "assistant", "content": "Hi Sarah! I've noted your interest in an office space in West Cairo. To help me find the best match, what is your budget and timeline?"},
    {"role": "user", "content": "My budget is 500k USD and I want to move in immediately."}
]

res = requests.post(f"{base_url}/api/chat", json={
    "session_id": session_id,
    "messages": messages
})

print(res.text)
