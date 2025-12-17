from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: dict):
    message = payload.get("message", "")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "question": message,
        "answer": f"Current UTC time is {now}"
    }
