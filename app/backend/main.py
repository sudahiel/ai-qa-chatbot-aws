import json
import os
from datetime import datetime, timezone

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for local browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "null",  # when you open index.html via file://
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"))
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def ask_bedrock(message: str) -> str:
    body = {
        "inputText": message,
        "textGenerationConfig": {
            "maxTokenCount": 256,
            "temperature": 0.5,
            "topP": 0.9,
        },
    }

    resp = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(resp["body"].read())
    return result["results"][0]["outputText"].strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: dict):
    message = (payload.get("message") or "").strip()

    # Simple deterministic answer to satisfy the assignment example
    if message.lower() in {"what time is it?", "what time is it"}:
        now = datetime.now(timezone.utc).isoformat()
        return {"question": message, "answer": f"Current UTC time is {now}"}

    if not message:
        return {"question": "", "answer": "Please provide a message."}

    # Otherwise use Bedrock (ECS will work via task role; local may not)
    try:
        answer = ask_bedrock(message)
    except Exception as e:
        answer = f"[bedrock_error] {type(e).__name__}: {str(e)}"

    return {"question": message, "answer": answer}

