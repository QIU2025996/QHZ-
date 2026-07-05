import json, urllib.request, os

with open('/tmp/pr.diff') as f:
    diff = f.read()
with open('/tmp/gemini-review.md') as f:
    gemini = f.read()

prompt = "You are an expert code reviewer. Gemini already reviewed this PR below. Provide your own analysis.\n\nGemini review:\n" + gemini + "\n\nDiff:\n" + diff

data = json.dumps({
    "model": "step-3.7-flash",
    "messages": [{"role": "user", "content": prompt}]
}).encode()

req = urllib.request.Request(
    "https://api.stepfun.com/step_plan/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ["STEPFUN_API_KEY"]
    }
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
    text = result["choices"][0]["message"]["content"]
    with open("/tmp/stepfun-review.md", "w") as f:
        f.write(text)
