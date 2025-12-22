import logging
import random
import string
from contextvars import ContextVar

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def _generate_trace_id(length: int = 12) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def get_trace_id() -> str:
    tid = _trace_id_var.get()
    if not tid:
        tid = _generate_trace_id()
        _trace_id_var.set(tid)
    return tid


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id or _generate_trace_id())


class TraceIDFilter(logging.Filter):
    """Logging filter injecting a `trace_id` attribute into LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.trace_id = get_trace_id()
        except Exception:
            record.trace_id = "unknown"
        return True


def setup_observability(logger: logging.Logger | None = None) -> None:
    """
    Attach TraceIDFilter and ensure format includes trace ID.

    If `logger` is None, configure the root logger.
    """
    target = logger or logging.getLogger()
    # Attach filter to logger and all handlers
    filt = TraceIDFilter()
    target.addFilter(filt)
    for h in target.handlers:
        h.addFilter(filt)
        # Ensure formatter includes trace ID
        fmt = h.formatter
        desired = "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"
        if fmt is None or getattr(fmt, '_fmt', '') != desired:
            h.setFormatter(logging.Formatter(desired))
