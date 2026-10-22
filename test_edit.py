import httpx

story = open("sample.txt").read()

response = httpx.post(
    "http://localhost:8000/edit",
    json={"story": story},
    timeout=300,
)
response.raise_for_status()

for s in response.json()["suggestions"]:
    print(f"[{s['type'].upper()}]")
    print("  BEFORE:", s["quote"])
    print("  AFTER: ", s["replacement"] or "(cut)")
    print("  NOTE:  ", s["note"])
    print()