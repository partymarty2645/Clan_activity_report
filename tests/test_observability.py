import logging
from io import StringIO

from core.observability import get_trace_id, set_trace_id, setup_observability, TraceIDFilter


def test_trace_id_generation():
    tid = get_trace_id()
    assert isinstance(tid, str) and len(tid) >= 8


def test_trace_id_persistence_in_context():
    tid1 = get_trace_id()
    tid2 = get_trace_id()
    assert tid1 == tid2
    # After set, should change
    set_trace_id("abc123xyz")
    assert get_trace_id() == "abc123xyz"


def test_logging_includes_trace_id():
    logger = logging.getLogger("ObsTest")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    setup_observability(logger)
    set_trace_id("trace-999")

    logger.info("hello")
    output = stream.getvalue()
    assert "trace-999" in output
    assert "hello" in output

