"""Telemetry module for Cloud Monitoring metrics."""

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from google.cloud import monitoring_v3

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("google-cloud-monitoring not available, telemetry disabled")


class Telemetry:
    """Telemetry client for Cloud Monitoring metrics."""

    def __init__(self, project_id: str | None = None) -> None:
        """Initialize telemetry client.

        Args:
            project_id: GCP project ID. If None, will try to get from environment.

        """
        if not MONITORING_AVAILABLE:
            self.enabled = False
            logger.warning("Telemetry disabled: google-cloud-monitoring not installed")
            return

        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if not self.project_id:
            self.enabled = False
            logger.warning("Telemetry disabled: GCP project ID not found")
            return

        try:
            self.client = monitoring_v3.MetricServiceClient()
            self.project_name = f"projects/{self.project_id}"
            self.enabled = True
            logger.info("Telemetry initialized for project: %s", self.project_id)
        except Exception as e:  # noqa: BLE001
            self.enabled = False
            logger.warning("Telemetry disabled: failed to initialize client: %s", e)

    def _create_time_series(
        self,
        metric_type: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Create a time series data point.

        Args:
            metric_type: The metric type (e.g., 'custom.googleapis.com/main_service/message_processing_duration')
            value: The metric value
            labels: Optional labels for the metric

        """
        if not self.enabled:
            return

        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = metric_type

            # Set metric labels
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = str(val)

            # Set resource (Cloud Run revision)
            series.resource.type = "cloud_run_revision"
            series.resource.labels["project_id"] = self.project_id
            service_name = os.getenv("K_SERVICE", "main-service")
            revision_name = os.getenv("K_REVISION", "unknown")
            location = os.getenv("CLOUD_RUN_REGION", "us-central1")
            series.resource.labels["service_name"] = service_name
            series.resource.labels["revision_name"] = revision_name
            series.resource.labels["location"] = location

            # Create timestamp
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)

            # Create data point
            point = monitoring_v3.Point()
            point.value.double_value = value
            point.interval.end_time.seconds = seconds
            point.interval.end_time.nanos = nanos
            series.points = [point]

            # Write time series
            self.client.create_time_series(
                name=self.project_name,
                time_series=[series],
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to write metric %s: %s", metric_type, e)

    def record_message_processing(
        self,
        duration_seconds: float,
        success: bool,  # noqa: FBT001
        error_type: str | None = None,
    ) -> None:
        """Record message processing metrics.

        Args:
            duration_seconds: Time taken to process the message
            success: Whether processing was successful
            error_type: Type of error if processing failed

        """
        # Record duration
        self._create_time_series(
            "custom.googleapis.com/main_service/message_processing_duration",
            duration_seconds,
        )

        # Record success/failure counter
        status = "success" if success else "failure"
        self._create_time_series(
            "custom.googleapis.com/main_service/message_processing_total",
            1.0,
            labels={"status": status},
        )

        # Record error type if applicable
        if not success and error_type:
            self._create_time_series(
                "custom.googleapis.com/main_service/message_processing_errors_total",
                1.0,
                labels={"error_type": error_type},
            )

    def record_poll_cycle(self, duration_seconds: float) -> None:
        """Record poll cycle metrics.

        Args:
            duration_seconds: Time taken for the poll cycle

        """
        self._create_time_series(
            "custom.googleapis.com/main_service/poll_cycle_duration",
            duration_seconds,
        )
        self._create_time_series(
            "custom.googleapis.com/main_service/poll_cycles_total",
            1.0,
        )

    @contextmanager
    def measure_message_processing(self, error_type_map: dict[type[Exception], str] | None = None) -> Iterator[None]:
        """Context manager to measure message processing time and success/failure.

        Args:
            error_type_map: Optional mapping of exception types to error type strings

        Yields:
            None

        """
        start_time = time.time()
        success = True
        error_type = None

        try:
            yield
        except Exception as e:
            success = False
            error_type = error_type_map.get(type(e), type(e).__name__) if error_type_map else type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self.record_message_processing(duration, success, error_type)

    @contextmanager
    def measure_poll_cycle(self) -> Iterator[None]:
        """Context manager to measure poll cycle duration.

        Yields:
            None

        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_poll_cycle(duration)


# Global telemetry instance
_telemetry: Telemetry | None = None


def get_telemetry() -> Telemetry:
    """Get or create the global telemetry instance.

    Returns:
        Telemetry instance

    """
    global _telemetry  # noqa: PLW0603
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry
