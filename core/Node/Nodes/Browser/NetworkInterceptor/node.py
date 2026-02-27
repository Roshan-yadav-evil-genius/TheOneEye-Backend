"""
NetworkInterceptor Node

Single Responsibility: Capture network requests and responses from JS-heavy websites using Playwright.
"""

import json
from typing import Optional, List, Dict, Any
import asyncio
import structlog
import re
import json
import time
import ast
from rich import print

from playwright.async_api import Page, Request, Response

from django.conf import settings

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from apps.browsersession.services.domain_throttle_service import wait_before_request
from ....Core.Form import BaseForm
from .form import NetworkInterceptorForm
from .._shared.BrowserManager import BrowserManager
from .._shared.services.session_resolver import extract_domain_from_url

logger = structlog.get_logger(__name__)


class NetworkInterceptor(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "playwright-network-interceptor"

    def get_form(self) -> Optional[BaseForm]:
        return NetworkInterceptorForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def setup(self):
        """Initialize BrowserManager connection."""
        self.browser_manager = BrowserManager()
        headless = getattr(settings, 'PLAYWRIGHT_HEADLESS', False)
        await self.browser_manager.initialize(headless=headless)

    def _extract_urls(self, node_data: NodeOutput) -> List[str]:
        """
        Extract and normalize URLs from the form field.
        
        Args:
            node_data: The NodeOutput containing input data (not directly used for URL extraction).
            
        Returns:
            List of URL strings
        """
        # Check form field first
        urls_value = self.form.cleaned_data.get("urls")
        urls = []

        try:
            urls_value = ast.literal_eval(urls_value)
        except (ValueError, SyntaxError):
            pass

        if urls_value:
            # Handle form field value (may be string or list after Jinja rendering)
            if isinstance(urls_value, list):
                # Already a list from Jinja template
                urls = [str(url).strip() for url in urls_value if url and str(url).strip()]
            elif isinstance(urls_value, str):
                # Newline-separated string
                urls = [url.strip() for url in urls_value.split('\n') if url.strip()]
            else:
                # Convert to string and split
                urls = [str(urls_value).strip()]

        if urls:
            logger.info("Using URLs from form field", url_count=len(urls), node_id=self.node_config.id)
            return urls

        
        # No URLs found
        raise ValueError("No URLs provided. Please provide URLs in form field 'urls'.")

    def _parse_response_size(self, size_str: str) -> Optional[int]:
        """
        Parse size string (e.g., "10MB", "1GB", "500KB") to bytes.
        
        Uses 1024-based conversion (KB=1024, MB=1024*1024, etc.)
        Case-insensitive.
        
        Args:
            size_str: Size string like "10MB", "1GB", "500KB"
            
        Returns:
            Integer bytes or None if invalid format
        """
        if not size_str or not size_str.strip():
            return None
        
        size_str = size_str.strip().upper()
        
        # Match pattern: number followed by unit (KB, MB, GB)
        match = re.match(r'^(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)$', size_str)
        if not match:
            logger.warning("Invalid size format", size_str=size_str, node_id=self.node_config.id)
            return None
        
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to bytes (1024-based)
        multipliers = {
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024,
        }
        
        return int(value * multipliers[unit])

    def _should_capture_request(self, request: Request) -> bool:
        """
        Determine if a request should be captured based on user filters.
        
        Args:
            request: Playwright Request object
            
        Returns:
            True if request should be captured, False otherwise
        """
        # Get resource type filter
        resource_types = self.form.cleaned_data.get('capture_resource_types', 'xhr,fetch')
        if resource_types != 'all':
            allowed_types = [t.strip() for t in resource_types.split(',')]
            if request.resource_type not in allowed_types:
                logger.debug(
                    "Request filtered by resource type",
                    url=request.url,
                    resource_type=request.resource_type,
                    allowed=allowed_types,
                    node_id=self.node_config.id
                )
                return False
        
        # Get URL pattern filter
        url_pattern = self.form.cleaned_data.get('url_pattern', '').strip()
        if url_pattern:
            try:
                if not re.search(url_pattern, request.url):
                    logger.debug(
                        "Request filtered by URL pattern",
                        url=request.url,
                        pattern=url_pattern,
                        node_id=self.node_config.id
                    )
                    return False
            except re.error as e:
                logger.warning(
                    "Invalid regex pattern",
                    pattern=url_pattern,
                    error=str(e),
                    node_id=self.node_config.id
                )
                # If regex is invalid, don't filter (capture all)
        
        # Get HTTP method filter
        http_methods = self.form.cleaned_data.get('http_methods', 'all')
        if http_methods != 'all':
            allowed_methods = [m.strip() for m in http_methods.split(',')]
            if request.method not in allowed_methods:
                logger.debug(
                    "Request filtered by HTTP method",
                    url=request.url,
                    method=request.method,
                    allowed=allowed_methods,
                    node_id=self.node_config.id
                )
                return False
        
        return True

    def _should_capture_response(self, response: Response) -> bool:
        """
        Determine if a response should be captured based on user filters.
        
        Args:
            response: Playwright Response object
            
        Returns:
            True if response should be captured, False otherwise
        """
        # Get status code filter
        status_codes = self.form.cleaned_data.get('status_codes', '').strip()
        if status_codes:
            try:
                allowed_codes = [int(c.strip()) for c in status_codes.split(',') if c.strip()]
                if response.status not in allowed_codes:
                    logger.debug(
                        "Response filtered by status code",
                        url=response.url,
                        status=response.status,
                        allowed=allowed_codes,
                        node_id=self.node_config.id
                    )
                    return False
            except ValueError:
                logger.warning(
                    "Invalid status code format",
                    status_codes=status_codes,
                    node_id=self.node_config.id
                )
                # If format is invalid, don't filter (capture all)
        
        return True

    def _response_matches_filters(self, response: Response) -> bool:
        """
        Predicate function for wait_for_response to check if response matches all filters.
        
        This is used to immediately return when a matching response is found.
        Note: Response objects don't have resource_type, so we can only check URL pattern and status.
        
        Args:
            response: Playwright Response object
            
        Returns:
            True if response matches all applicable filters, False otherwise
        """
        # Check URL pattern filter
        url_pattern = self.form.cleaned_data.get('url_pattern', '').strip()
        if url_pattern:
            try:
                if not re.search(url_pattern, response.url):
                    return False
            except re.error:
                # Invalid regex, don't filter (match all)
                pass
        
        # Check status code filter
        if not self._should_capture_response(response):
            return False
        
        # Note: We can't check resource_type or HTTP method from response object alone
        # These filters are applied during request tracking, but for immediate return
        # we rely on URL pattern and status code matching
        
        return True

    async def _fetch_response_body(self, response: Response) -> Optional[Any]:
        """
        Fetch and parse response body asynchronously.
        
        Args:
            response: Playwright Response object
            
        Returns:
            Parsed JSON dict, text string, or None on error/skip
        """
        # Check if body should be included
        include_body = self.form.cleaned_data.get('include_response_body', 'true')
        if include_body == 'false':
            return None
        
        # Get max size limit
        max_size_str = self.form.cleaned_data.get('max_response_size', '10MB')
        max_size_bytes = self._parse_response_size(max_size_str)
        
        # Check content-length header first if available
        content_length = response.headers.get('content-length')
        if content_length and max_size_bytes:
            try:
                content_length_int = int(content_length)
                if content_length_int > max_size_bytes:
                    logger.debug(
                        "Response body skipped (too large by content-length)",
                        url=response.url,
                        size=content_length_int,
                        max=max_size_bytes,
                        node_id=self.node_config.id
                    )
                    return None
            except ValueError:
                # Invalid content-length, continue to fetch and check actual size
                pass
        
        try:
            # Fetch response body
            body = await response.body()
            
            # Check actual size
            if max_size_bytes and len(body) > max_size_bytes:
                logger.debug(
                    "Response body skipped (too large)",
                    url=response.url,
                    size=len(body),
                    max=max_size_bytes,
                    node_id=self.node_config.id
                )
                return None
            
            # Get content-type
            content_type = response.headers.get('content-type', '').lower()
            
            # Try to parse as JSON if content-type suggests it
            if 'application/json' in content_type:
                try:
                    return json.loads(body.decode('utf-8'))
                except json.JSONDecodeError:
                    # Fallback to text if JSON parsing fails
                    return body.decode('utf-8', errors='ignore')
            else:
                # Decode as text
                return body.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.warning(
                "Failed to fetch response body",
                url=response.url,
                error=str(e),
                node_id=self.node_config.id
            )
            return None

    async def _load_single_url_with_interception(self, url: str, context, session_name: str) -> dict:
        page = None
        response_event = asyncio.Event()
        matching_response: Optional[Response] = None
        captured_requests: Dict[str, Dict[str, Any]] = {}
        goto_task = None

        try:
            respect_throttle = self.form.cleaned_data.get("respect_domain_throttle", True)
            if respect_throttle:
                await wait_before_request(session_name, url)
            # Get timeout from form
            return_timeout_str = self.form.cleaned_data.get('return_timeout', '30000')
            try:
                return_timeout_ms = int(return_timeout_str)
            except (ValueError, TypeError):
                return_timeout_ms = 30000  # Default to 30 seconds
            
            timeout_seconds = return_timeout_ms / 1000.0 if return_timeout_ms > 0 else None
            goto_timeout_ms = return_timeout_ms if return_timeout_ms > 0 else 300000  # Long timeout when waiting indefinitely

            page = await context.new_page()
            
            # Define request callback to track requests
            def on_request(request: Request):
                if self._should_capture_request(request):
                    captured_requests[request.url] = {
                        'url': request.url,
                        'method': request.method,
                        'headers': dict(request.headers),
                        'post_data': request.post_data,
                        'resource_type': request.resource_type,
                        'timestamp': time.time()
                    }
            
            # Define response callback that checks filters and sets event
            def on_response(response: Response):
                nonlocal matching_response
                if not response_event.is_set() and self._response_matches_filters(response):
                    matching_response = response
                    response_event.set()
            
            page.on('request', on_request)
            page.on('response', on_response)

            # Start navigation in background (commit = minimal wait, page starts loading)
            goto_task = asyncio.create_task(page.goto(url, wait_until='commit', timeout=goto_timeout_ms))
            response_task = asyncio.create_task(response_event.wait())

            # Wait only for matching response until timeout (or indefinitely if return_timeout=0)
            if timeout_seconds is not None:
                done, pending = await asyncio.wait(
                    [response_task],
                    timeout=timeout_seconds,
                    return_when=asyncio.FIRST_COMPLETED
                )
            else:
                await response_event.wait()
                done, pending = {response_task}, set()

            # Cancel and await background goto to avoid pending-task warnings
            if goto_task and not goto_task.done():
                goto_task.cancel()
            if goto_task:
                await asyncio.gather(goto_task, return_exceptions=True)
            for task in pending:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

            # Success: matching network response was found
            if response_task in done and not response_task.cancelled():
                if response_task.exception():
                    raise response_task.exception()
                if matching_response is None:
                    raise Exception("Response event fired but no response object was captured.")

                body = await self._fetch_response_body(matching_response)
                response_data = {
                    'url': matching_response.url, 'status': matching_response.status,
                    'status_text': matching_response.status_text, 'headers': dict(matching_response.headers), 'body': body
                }
                request_data = captured_requests.get(matching_response.url)
                
                logger.info("Matching response found, returning immediately", url=url, response_url=matching_response.url, node_id=self.node_config.id)
                return {
                    "url": url, "final_url": page.url, "dom_content": None,
                    "network_requests": [{"request": request_data, "response": response_data}]
                }

            # No matching response in time (timeout)
            error_message = f"Timeout: No matching response found within {return_timeout_ms}ms."
            logger.warning(error_message, url=url, timeout=return_timeout_ms, node_id=self.node_config.id)
            return {
                "url": url, "final_url": page.url, "dom_content": None,
                "network_requests": [], "error": error_message
            }

        except Exception as e:
            logger.error("Failed to load webpage with network interception", url=url, error=str(e), node_id=self.node_config.id)
            if goto_task and not goto_task.done():
                goto_task.cancel()
            if goto_task:
                await asyncio.gather(goto_task, return_exceptions=True)
            return {
                "url": url,
                "final_url": page.url if page and not page.is_closed() else None,
                "dom_content": None,
                "network_requests": [],
                "error": str(e)
            }
        finally:
            if page:
                try:
                    await page.close()
                    logger.debug("Page closed", url=url, node_id=self.node_config.id)
                except Exception as close_error:
                    logger.warning("Error closing page", url=url, error=str(close_error), node_id=self.node_config.id)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Load multiple webpages with network interception using Playwright in parallel.

        Navigation uses wait_until='commit'; the node waits only for a matching network
        response until return_timeout. No page content is returned.

        Inputs:
            node_data.data["urls"]: List of URLs to load (optional).
            node_data.data["url"]: Single URL to load (optional, backward compatibility).

        Form Config:
            urls: URLs to load (newline-separated string or Jinja template like {{ data.urls }}).
            session_name: Name of the persistent context session.
            capture_resource_types: Types of requests to capture (xhr, fetch, xhr,fetch, all).
            url_pattern: Optional regex pattern to filter URLs.
            http_methods: HTTP methods to capture (GET, POST, GET,POST, all).
            status_codes: Optional comma-separated status codes to filter.
            include_response_body: Whether to capture response bodies (true/false).
            max_response_size: Maximum response size to capture (e.g., "10MB").
            return_timeout: Maximum time to wait for matching response in milliseconds.
        """
        session_name = self.form.cleaned_data.get("session_name", "default")

        urls = self._extract_urls(node_data)
        domain = extract_domain_from_url(urls[0]) if urls else None

        logger.info(
            "Starting network interception",
            urls=urls,
            url_count=len(urls),
            session=session_name,
            node_id=self.node_config.id,
        )

        context, resolved_session_id = await self.browser_manager.get_context(session_name, domain=domain)

        tasks = [
            self._load_single_url_with_interception(url, context, resolved_session_id)
            for url in urls
        ]
        
        # Use asyncio.gather with return_exceptions to handle errors gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and format output
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle unexpected exceptions
                logger.error(
                    "Unexpected error loading URL with network interception",
                    url=urls[i],
                    error=str(result),
                    node_id=self.node_config.id
                )
                formatted_results.append({
                    "url": urls[i],
                    "final_url": None,
                    "dom_content": None,
                    "network_requests": [],
                    "error": str(result)
                })
            else:
                # Result is a dict from _load_single_url_with_interception
                formatted_results.append(result)
        
        logger.info(
            "Network interception completed for all URLs",
            total=len(formatted_results),
            successful=sum(1 for r in formatted_results if len(r.get("network_requests", [])) > 0),
            failed=sum(1 for r in formatted_results if r.get("error") is not None),
            node_id=self.node_config.id
        )
        
        # Store results in the requested format
        output_key = self.get_unique_output_key(node_data, "network_interceptor")
        node_data.data[output_key] = formatted_results

        return node_data
