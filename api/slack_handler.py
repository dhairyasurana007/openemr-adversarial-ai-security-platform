from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status

router = APIRouter(prefix="/api/slack", tags=["slack"])

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")


def _verify_slack_signature(timestamp: str, signature: str, body: bytes) -> bool:
    if not SLACK_SIGNING_SECRET:
        return False
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    base = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"), base, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def slack_webhook(
    request: Request,
    x_slack_signature: str = Header(alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(alias="X-Slack-Request-Timestamp"),
) -> dict:
    body = await request.body()
    if not _verify_slack_signature(x_slack_request_timestamp, x_slack_signature, body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature",
        )

    payload = await request.form()
    action_payload = json.loads(payload.get("payload", "{}"))
    decision = action_payload.get("decision", "unknown")
    vulnerability_id = action_payload.get("vulnerability_id")
    attack_id = action_payload.get("attack_id")

    target_id = vulnerability_id or attack_id
    if target_id:
        UUID(str(target_id))

    return {"ok": True, "decision": decision, "target_id": target_id}
