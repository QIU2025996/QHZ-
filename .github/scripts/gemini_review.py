import json, urllib.request, os

# Read diff
with open('/tmp/pr.diff') as f:
    diff = f.read()

prompt = "You are an expert code reviewer. Review this pull request diff and provide a structured review with: 1) SUMMARY 2) ISSUES with severity (CRITICAL/HIGH/MEDIUM/LOW) 3) SUGGESTIONS 4) VERDICT.\n\nDiff:\n" + diff

data = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}]
}).encode()

req = urllib.request.Request(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=" + os.environ.get("GEMINI_API_KEY", ""),
    data=data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
    text = ""
    if result.get("candidates"):
        for p in result["candidates"][0].get("content", {}).get("parts", []):
            text += p.get("text", "")
    with open("/tmp/gemini-review.md", "w") as f:
        f.write(text or "Error: No response from Gemini")
