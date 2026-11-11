"""
Tracker 03.05 - Batch ID Generation

Requirement:
Create a unique batch/load ID for every accepted processing run.

Frozen project format:
BATCH_YYYYMMDD_HHMMSS_<short-id>
"""

from datetime import datetime
from uuid import uuid4


def generate_batch_id() -> str:
    """
    Generate a unique Batch ID for one controlled processing run.

    Format:
    BATCH_YYYYMMDD_HHMMSS_<short-id>
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid4().hex[:8]

    batch_id = f"BATCH_{timestamp}_{short_id}"

    return batch_id


if __name__ == "__main__":

    print("Starting Tracker 03.05 - Batch ID Generation")

    batch_id = generate_batch_id()

    print(f"Generated Batch ID: {batch_id}")

    print("Tracker 03.05 Batch ID generation test completed")