import os
import time
import logging
from google.cloud import monitoring_v3
from google.protobuf.timestamp_pb2 import Timestamp

logger = logging.getLogger(__name__)

# --- Client Initialization ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
try:
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{PROJECT_ID}"
except Exception as e:
    logger.warning(f"Could not initialize GCP Monitoring Client (this is normal if running locally): {e}")
    client = None
    project_name = None

# --- Centralized Time Series Creation (DRY Principle) ---
def _write_time_series(metric_type: str, metric_labels: dict):
    """
    Internal helper to create and write a single data point to Google Cloud Monitoring.
    This function contains the corrected, robust timestamp logic.
    """
    if not client or not PROJECT_ID:
        return

    try:
        series = monitoring_v3.TimeSeries()
        series.metric.type = metric_type
        
        # Attach all provided labels
        for key, val in metric_labels.items():
            series.metric.labels[key] = val
            
        # Set the resource type to 'global' as required by the API
        series.resource.type = "global"
        series.resource.labels["project_id"] = PROJECT_ID
        
        # Create a data point with a value of 1 (for counting events)
        point = monitoring_v3.Point()
        point.value.int64_value = 1
        
        # --- CORRECT TIMESTAMP LOGIC ---
        # This creates a google.protobuf.Timestamp object as required by the API.
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        point.interval.end_time = Timestamp(seconds=seconds, nanos=nanos)
        # --------------------------------
        
        series.points = [point]
        client.create_time_series(name=project_name, time_series=[series])
        
        logger.info(f"✅ Successfully wrote metric: {metric_type} with labels: {metric_labels}")

    except Exception as e:
        # Log the full traceback for detailed debugging
        logger.error(f"❌ Failed to write metric {metric_type}", exc_info=True)

# --- Public Functions to be Called by Agents ---
def record_agent_invocation(agent_name: str):
    """Records that a specific agent was called."""
    _write_time_series(
        metric_type="custom.googleapis.com/agent/invocation_count",
        metric_labels={"agent_name": agent_name}
    )

def record_fallback_event(agent_name: str, reason: str):
    """Records that an agent hit a fallback scenario."""
    _write_time_series(
        metric_type="custom.googleapis.com/agent/fallback_count",
        metric_labels={"agent_name": agent_name, "reason": reason}
    )
