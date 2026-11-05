import json
import logging
import os
from uuid import UUID

import boto3

logger = logging.getLogger("talentmatch.events")

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME", "default")

events = boto3.client(
    "events",
    endpoint_url=(
        os.getenv("EVENTBRIDGE_ENDPOINT_URL")
        or os.getenv("AWS_ENDPOINT_URL")
        or None
    ),
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)


def publish_resume_completed(upload_id: UUID) -> bool:
    """Publish a minimal resume-completion event to EventBridge."""
    try:
        response = events.put_events(
            Entries=[
                {
                    "Source": "talentmatch.resume",
                    "DetailType": "Resume Processing Completed",
                    "EventBusName": EVENT_BUS_NAME,
                    "Detail": json.dumps(
                        {
                            "upload_id": str(upload_id),
                            "status": "completed",
                        }
                    ),
                }
            ]
        )

        if response.get("FailedEntryCount", 0) > 0:
            logger.error(
                "EventBridge rejected completion event for upload %s: %s",
                upload_id,
                response.get("Entries"),
            )
            return False

        logger.info(
            "Published completion event for upload %s",
            upload_id,
        )
        return True

    except Exception:
        logger.exception(
            "Could not publish completion event for upload %s",
            upload_id,
        )
        return False
