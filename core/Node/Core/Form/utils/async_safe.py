"""
Async-Safe Execution Utility

Single Responsibility: Run async functions safely from either sync or async contexts.

This module provides utilities for calling async functions when you don't know
if you're currently in a sync or async context. This is particularly useful for
form loaders that need to call async APIs but may be invoked during node execution
(async context) or form schema generation (sync context).
"""

import asyncio
import concurrent.futures
from typing import TypeVar, Callable, Any

T = TypeVar('T')


def run_async_safe(async_func: Callable[..., T], *args: Any, timeout: float = 30, **kwargs: Any) -> T:
    """
    Run an async function from either sync or async context.
    
    This function detects the current context and uses the appropriate method:
    - In sync context: Uses async_to_sync directly
    - In async context: Runs in a separate thread with its own event loop
    
    This pattern is needed because async_to_sync fails when there's already
    a running event loop (e.g., during node execution).
    
    Args:
        async_func: The async function to execute
        *args: Positional arguments to pass to the function
        timeout: Maximum time to wait for execution (default: 30 seconds)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the async function
        
    Raises:
        TimeoutError: If execution exceeds the timeout
        Exception: Any exception raised by the async function
        
    Example:
        # Instead of:
        from asgiref.sync import async_to_sync
        result = async_to_sync(populate_spreadsheet_choices)(account_id)
        
        # Use:
        from Node.Core.Form.utils import run_async_safe
        result = run_async_safe(populate_spreadsheet_choices, account_id)
    """
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        
        # We're in an async context - can't use async_to_sync
        # Run in a separate thread with its own event loop
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=timeout)
            
    except RuntimeError:
        # No running event loop - we're in sync context
        # Safe to use async_to_sync
        from asgiref.sync import async_to_sync
        return async_to_sync(async_func)(*args, **kwargs)
