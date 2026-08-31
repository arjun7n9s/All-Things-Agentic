"""FIRMS batch + EE task publish. Topics created in hour-0: firms-batches, firms-ee-tasks."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def pubsub_enabled() -> bool:
    return os.environ.get("TMC_PUBSUB") == "enabled"


def project_id() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or "all-things-agents-507211"
    )


def publish_wake_batch(
    *,
    case: str,
    firms_ids: list[str],
    detections: int,
    matches: int,
    write_happened: bool,
    bq_job_id: str | None = None,
    ee_job_id: str | None = None,
) -> dict:
    """Publish wake witness to Pub/Sub. Never blocks MATCH; outage is recorded."""
    if not pubsub_enabled():
        return {"published": False, "reason": "pubsub_not_enabled"}
    topic = os.environ.get("FIRMS_BATCH_TOPIC", "firms-batches")
    ee_topic = os.environ.get("FIRMS_EE_TOPIC", "firms-ee-tasks")
    payload = {
        "case": case,
        "firms_ids": firms_ids[:64],
        "detections": detections,
        "matches": matches,
        "write_happened": write_happened,
        "bq_job_id": bq_job_id,
        "ee_job_id": ee_job_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "fixture_tmc": "Coast Range TMC",
    }
    try:
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        batch_path = publisher.topic_path(project_id(), topic)
        ee_path = publisher.topic_path(project_id(), ee_topic)
        data = json.dumps(payload).encode("utf-8")
        batch_id = publisher.publish(batch_path, data, case=case).result(timeout=30)
        ee_id = None
        if ee_job_id or matches:
            ee_id = publisher.publish(
                ee_path,
                json.dumps(
                    {
                        "case": case,
                        "ee_job_id": ee_job_id,
                        "firms_ids": firms_ids[:16],
                        "published_at": payload["published_at"],
                    }
                ).encode("utf-8"),
                case=case,
            ).result(timeout=30)
        return {
            "published": True,
            "firms_batches_message_id": batch_id,
            "firms_ee_tasks_message_id": ee_id,
            "topic": topic,
            "ee_topic": ee_topic,
        }
    except Exception as exc:
        return {"published": False, "reason": f"pubsub_publish_failed:{exc}"}
