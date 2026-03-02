import httpx
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"c:\Users\excalibur\Desktop\Projeler\Intellium\IntelliumAIBackend\backendnew\test_data\sample_transcript.json"

r = httpx.post(
    "http://localhost:8001/chat/mulakat-degerlendirme/",
    json={
        "userId": "test-user-001",
        "firstName": "Elif",
        "lastName": "Demir",
        "email": "elif.demir@test.com",
        "transcriptPath": path,
    },
    timeout=1200,
)

print("STATUS:", r.status_code)
print("HEADERS:", dict(r.headers))
raw = r.text
print("RAW LENGTH:", len(raw))
if not raw:
    print("EMPTY RESPONSE - server may have errored")
    sys.exit(1)
print("RAW[:500]:", raw[:500])
d = r.json()
print("SUCCESS:", d.get("success"))
print("TOTAL_TIME:", d.get("totalTime"), "s")
print("TOTAL_MINUTES:", d.get("totalTimeMinutes"), "dk")
print("WEBHOOK_SENT:", d.get("webhookSent"))
print()

print("=== TASKS ===")
tasks = d.get("tasks") or {}
for k, v in tasks.items():
    err_msg = " ERR: " + str(v.get("error")) if v.get("error") else ""
    print(f"  {k}: {v['status']} ({v['duration']}s){err_msg}")

print()

sections = [
    ("PUANLAMA TABLOSU", "puanlamaTablosu"),
    ("RECRUITER NOTU", "recruiterNotu"),
    ("TEKNIK YETKINLIK", "teknikYetkinlik"),
    ("SOFT SKILL ANALIZI", "softSkillAnalizi"),
]

for title, key in sections:
    content = d.get(key) or ""
    print(f"=== {title} ({len(content)} chars) ===")
    print(content[:400])
    if len(content) > 400:
        print("...")
    print()

print("ERROR:", d.get("error"))
