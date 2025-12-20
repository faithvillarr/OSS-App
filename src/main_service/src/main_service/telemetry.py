"""Telemetry module using OpenTelemetry for metrics collection."""

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

logger = logging.getLogger(__name__)
if not TELEMETRY_AVAILABLE:
    logger.warning("OpenTelemetry not available, telemetry disabled")


class Telemetry:
    """Telemetry client using OpenTelemetry Metrics API."""

    def __init__(self, otlp_endpoint: str | None = None) -> None:
        """Initialize telemetry client.

        Args:
            otlp_endpoint: OTLP exporter endpoint. Defaults to localhost:4317 or from OTEL_EXPORTER_OTLP_ENDPOINT env var.

        """
        if not TELEMETRY_AVAILABLE:
            self.enabled = False
            logger.warning("Telemetry disabled: OpenTelemetry not installed")
            return

        # Get OTLP endpoint from parameter, environment variable, or default
        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        try:
            # Create resource with Cloud Run metadata
            resource_attributes: dict[str, str] = {
                "service.name": os.getenv("K_SERVICE", "main-service"),
                "service.namespace": os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "unknown",
            }

            # Add Cloud Run specific attributes if available
            if revision := os.getenv("K_REVISION"):
                resource_attributes["cloud.run.revision"] = revision
            if region := os.getenv("CLOUD_RUN_REGION"):
                resource_attributes["cloud.region"] = region

            resource = Resource.create(resource_attributes)

            # Create OTLP exporter
            exporter = OTLPMetricExporter(
                endpoint=endpoint,
                insecure=True,  # Use insecure for localhost communication
            )

            # Create metric reader with async export
            reader = PeriodicExportingMetricReader(
                exporter=exporter,
                export_interval_millis=10000,  # Export every 10 seconds
            )

            # Create meter provider
            self.meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[reader],
            )

            # Set global meter provider
            metrics.set_meter_provider(self.meter_provider)

            # Get meter
            self.meter = metrics.get_meter(__name__)

            # Create metric instruments
            self.message_processing_duration = self.meter.create_histogram(
                name="message_processing_duration",
                description="End-to-end latency from message processing start to response posting (seconds)",
                unit="s",
            )

            self.message_processing_total = self.meter.create_counter(
                name="message_processing_total",
                description="Total number of messages processed, labeled by status (success/failure)",
                unit="1",
            )

            self.enabled = True
            logger.info("Telemetry initialized with OTLP endpoint: %s", endpoint)
        except Exception as e:  # noqa: BLE001
            self.enabled = False
            logger.warning("Telemetry disabled: failed to initialize OpenTelemetry: %s", e)

    def record_message_processing(
        self,
        duration_seconds: float,
        success: bool,  # noqa: FBT001
        error_type: str | None = None,  # noqa: ARG002
    ) -> None:
        """Record message processing metrics.

        Args:
            duration_seconds: Time taken to process the message (E2E latency)
            success: Whether processing was successful
            error_type: Deprecated, kept for backward compatibility but not used

        """
        if not self.enabled:
            return

        try:
            # Record duration (histogram)
            self.message_processing_duration.record(
                duration_seconds,
                attributes={"status": "success" if success else "failure"},
            )

            # Record success/failure counter
            # Success rate = message_processing_total{status="success"} / message_processing_total
            # Failure rate = message_processing_total{status="failure"} / message_processing_total
            status = "success" if success else "failure"
            self.message_processing_total.add(
                1,
                attributes={"status": status},
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to record message processing metric: %s", e)

    @contextmanager
    def measure_message_processing(self, error_type_map: dict[type[Exception], str] | None = None) -> Iterator[None]:  # noqa: ARG002
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
        except Exception:
            success = False
            error_type = None
            raise
        finally:
            duration = time.time() - start_time
            self.record_message_processing(duration, success=success, error_type=error_type)

    def shutdown(self) -> None:
        """Shutdown the telemetry client and flush remaining metrics."""
        if self.enabled and hasattr(self, "meter_provider"):
            try:
                self.meter_provider.shutdown()
            except Exception as e:  # noqa: BLE001
                logger.debug("Error shutting down meter provider: %s", e)


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
