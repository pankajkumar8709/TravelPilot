"""Phase 0 — prove the EventBridge->SQS->Lambda pipeline with a forced test event.

Sends one probe message to the SQS queue; the Lambda logs it and returns.
Confirms the plumbing works even when the scheduled poll fires nothing real.

Usage (after `sam deploy`):
  set QUEUE_URL=<the QueueUrl output from sam deploy>
  python send_test_event.py
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    queue_url = os.environ.get("QUEUE_URL", "")
    if not queue_url:
        print("Set QUEUE_URL to the QueueUrl output from `sam deploy`.")
        return 2
    try:
        import boto3

        sqs = boto3.client("sqs")
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"probe": True}))
        print("Sent probe message. Check CloudWatch logs for travelpilot-disruption-worker:")
        print("  expect: '[disruption-worker] probe/tick received — pipeline OK'")
        return 0
    except Exception as e:  # noqa: BLE001
        print("FAILED:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
