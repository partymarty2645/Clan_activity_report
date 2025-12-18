"""
Utility decorators and helpers for performance and resilience
"""
import time
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, TypeVar, Optional

logger = logging.getLogger("Utils.Performance")

T = TypeVar('T')


def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator for async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. Retrying in {current_delay:.1f}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def timed_operation(operation_name: Optional[str] = None):
    """
    Decorator to log execution time of operations.
    Works with both sync and async functions.
    """
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.time() - start
                    logger.info(f"⏱️  {name} completed in {elapsed:.2f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start
                    logger.error(f"❌ {name} failed after {elapsed:.2f}s: {e}")
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start
                    logger.info(f"⏱️  {name} completed in {elapsed:.2f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start
                    logger.error(f"❌ {name} failed after {elapsed:.2f}s: {e}")
                    raise
            return sync_wrapper
    
    return decorator


class PerformanceMonitor:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"▶️  Starting: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"✅ Completed: {self.operation_name} ({elapsed:.2f}s)")
        else:
            logger.error(f"❌ Failed: {self.operation_name} ({elapsed:.2f}s) - {exc_val}")
        return False


def batch_process(items: list, batch_size: int = 100):
    """
    Generator that yields batches of items.
    Useful for processing large datasets in chunks.
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
