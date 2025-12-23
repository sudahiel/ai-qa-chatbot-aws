import os
from datetime import datetime, timezone

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI()

# CORS for local browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "null",  # when opening index.html via file://
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Environment variables
# -----------------------------------------------------------------------------

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"))
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

if not BEDROCK_MODEL_ID:
    raise RuntimeError("BEDROCK_MODEL_ID is not set")

print(f"[boot] AWS_REGION={AWS_REGION}")
print(f"[boot] BEDROCK_MODEL_ID={BEDROCK_MODEL_ID}")

# -----------------------------------------------------------------------------
# Bedrock client
# -----------------------------------------------------------------------------

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
)

# -----------------------------------------------------------------------------
# Bedrock helper
# -----------------------------------------------------------------------------

def ask_bedrock(message: str) -> str:
    """
    Call Amazon Bedrock using Converse API.
    This implementation targets on-demand models such as:
    - anthropic.claude-3-haiku-20240307-v1:0
    """
    response = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": message}],
            }
        ],
        inferenceConfig={
            "maxTokens": 256,
            "temperature": 0.5,
            "topP": 0.9,
        },
    )

    return response["output"]["message"]["content"][0]["text"].strip()

# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/health")
def api_health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(payload: dict):
    # Accept both "message" (canonical) and "question" (compat)
    message = (
        (payload.get("message") or "").strip()
        or (payload.get("question") or "").strip()
    )

    # Deterministic answer for assignment requirement
    if message.lower() in {"what time is it?", "what time is it"}:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "question": message,
            "answer": f"Current UTC time is {now}",
        }

    if not message:
        return {
            "question": "",
            "answer": "Please provide a message.",
        }

    # Bedrock AI response
    try:
        answer = ask_bedrock(message)
    except Exception as e:
        answer = f"[bedrock_error] {type(e).__name__}: {str(e)}"

    return {
        "question": message,
        "answer": answer,
    }
