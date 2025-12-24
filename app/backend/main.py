import json
import os
from datetime import datetime, timezone

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"))
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
if not BEDROCK_MODEL_ID:
    raise RuntimeError("BEDROCK_MODEL_ID is not set")

print(f"[boot] AWS_REGION={AWS_REGION}")
print(f"[boot] BEDROCK_MODEL_ID={BEDROCK_MODEL_ID}")

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def ask_bedrock(message: str) -> str:
    """
    - Titan Text Express: use InvokeModel with Titan schema
    - Others (Claude/Nova/...): use Converse API
    """
    mid = BEDROCK_MODEL_ID.strip()

    # 1) Titan path (most robust)
    if mid == "amazon.titan-text-express-v1" or mid.endswith("amazon.titan-text-express-v1"):
        body = {
            "inputText": message,
            "textGenerationConfig": {
                "maxTokenCount": 256,
                "temperature": 0.5,
                "topP": 0.9,
            },
        }
        resp = bedrock.invoke_model(
            modelId=mid,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(resp["body"].read())
        # Titan response shape
        outputs = result.get("results", [])
        if outputs and "outputText" in outputs[0]:
            return outputs[0]["outputText"].strip()
        return json.dumps(result)  # fallback for debugging

    # 2) Converse path (Claude/Nova etc.)
    resp = bedrock.converse(
        modelId=mid,
        messages=[{"role": "user", "content": [{"text": message}]}],
        inferenceConfig={"maxTokens": 256, "temperature": 0.5, "topP": 0.9},
    )
    return resp["output"]["message"]["content"][0]["text"].strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: dict):
    message = ((payload.get("message") or "").strip() or (payload.get("question") or "").strip())

    if message.lower() in {"what time is it?", "what time is it"}:
        now = datetime.now(timezone.utc).isoformat()
        return {"question": message, "answer": f"Current UTC time is {now}"}

    if not message:
        return {"question": "", "answer": "Please provide a message."}

    try:
        answer = ask_bedrock(message)
    except Exception as e:
        answer = f"[bedrock_error] {type(e).__name__}: {str(e)}"

    return {"question": message, "answer": answer}
