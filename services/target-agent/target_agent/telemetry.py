import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("agentsentry.events")


def emit(scan_id: str, test_id: str, kind: str, **fields: object) -> None:
    # Avoid logging resource contents, secrets, and prompts in the event stream.
    logger.info(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "scan_id": scan_id, "test_id": test_id, "event_type": kind, **fields}))

