"""Simple metrics collection for monitoring."""

from typing import Dict
from collections import defaultdict
import time
from threading import Lock

# Thread-safe metrics storage
_metrics_lock = Lock()
_metrics: Dict[str, any] = defaultdict(int)
_request_times: Dict[str, list] = defaultdict(list)


def increment_counter(name: str, value: int = 1):
    """Increment a counter metric."""
    with _metrics_lock:
        _metrics[f"counter_{name}"] += value


def record_request_time(endpoint: str, duration_ms: float):
    """Record request duration for an endpoint."""
    with _metrics_lock:
        _request_times[endpoint].append(duration_ms)
        # Keep only last 1000 requests
        if len(_request_times[endpoint]) > 1000:
            _request_times[endpoint] = _request_times[endpoint][-1000:]


def get_metrics() -> Dict:
    """Get all current metrics."""
    with _metrics_lock:
        result = dict(_metrics)
        
        # Calculate average request times
        for endpoint, times in _request_times.items():
            if times:
                result[f"avg_time_{endpoint}"] = sum(times) / len(times)
                result[f"max_time_{endpoint}"] = max(times)
                result[f"min_time_{endpoint}"] = min(times)
                result[f"count_{endpoint}"] = len(times)
        
        return result


def reset_metrics():
    """Reset all metrics (for testing)."""
    with _metrics_lock:
        _metrics.clear()
        _request_times.clear()

