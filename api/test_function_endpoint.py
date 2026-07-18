"""Quick smoke test for the /api/analyze-function/ endpoint."""
import json
import http.client

# Read auth.js content from disk
with open(r"D:\RippleGaurd\fixture_repo\auth.js", "r", encoding="utf-8") as f:
    old_content = f.read()

# Modify createSession body slightly
new_content = old_content.replace(
    "return { sessionId, userId };",
    "return { sessionId, userId, createdAt: Date.now() };"
)

payload = json.dumps({
    "repo_path": "D:/RippleGaurd/fixture_repo",
    "filepath": "D:/RippleGaurd/fixture_repo/auth.js",
    "old_content": old_content,
    "new_content": new_content,
})

conn = http.client.HTTPConnection("127.0.0.1", 8000)
conn.request("POST", "/api/analyze-function/", body=payload,
             headers={"Content-Type": "application/json"})
resp = conn.getresponse()
body = resp.read().decode("utf-8")
conn.close()

print(f"Status: {resp.status}")
print(json.dumps(json.loads(body), indent=2))
