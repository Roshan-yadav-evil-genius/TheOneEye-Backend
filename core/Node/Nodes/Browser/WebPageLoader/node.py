"""
WebPageLoader Node

Single Responsibility: Load webpages using Playwright browser automation.
"""

from typing import Optional, List
import asyncio
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import WebPageLoaderForm
from .._shared.BrowserManager import BrowserManager
from apps.browsersession.services.domain_throttle_service import wait_before_request

logger = structlog.get_logger(__name__)


class WebPageLoader(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "playwright-web-page-loader"

    def get_form(self) -> Optional[BaseForm]:
        return WebPageLoaderForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def setup(self):
        """Initialize BrowserManager connection."""
        self.browser_manager = BrowserManager()
        # Ensure browser manager is initialized (it's a singleton, so safe to call repeatedly)
        await self.browser_manager.initialize(
            headless=False
        )  # Default to visible functionality for now as per user preference likely

    def _extract_urls(self, node_data: NodeOutput) -> List[str]:
        """
        Extract and normalize URLs from form field or input data.
        
        Priority order:
        1. Form field 'urls' (may be newline-separated string or Jinja-rendered list/string)
        2. Input data 'urls' (list)
        3. Input data 'url' (single URL, for backward compatibility)
        
        Args:
            node_data: The NodeOutput containing input data
            
        Returns:
            List of URL strings
        """
        # Check form field first
        urls_value = self.form.cleaned_data.get("urls")
        
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
        
        # Fall back to input data 'urls' (list)
        input_urls = node_data.data.get("urls")
        if input_urls:
            if isinstance(input_urls, list):
                urls = [str(url).strip() for url in input_urls if url and str(url).strip()]
            else:
                # Single value, convert to list
                urls = [str(input_urls).strip()]
            
            if urls:
                logger.info("Using URLs from input data 'urls'", url_count=len(urls), node_id=self.node_config.id)
                return urls
        
        # Fall back to input data 'url' (single URL, backward compatibility)
        input_url = node_data.data.get("url")
        if input_url:
            url_str = str(input_url).strip()
            if url_str:
                logger.info("Using URL from input data 'url' (backward compatibility)", node_id=self.node_config.id)
                return [url_str]
        
        # No URLs found
        raise ValueError("No URLs provided. Please provide URLs in form field 'urls', or in input data as 'urls' (list) or 'url' (string).")

    async def _load_single_url(self, url: str, context, wait_mode: str, session_name: str) -> dict:
        """
        Load a single URL and return its DOM content.
        
        Args:
            url: The URL to load
            context: Browser context (already obtained, shared across parallel loads)
            wait_mode: Wait strategy for page loading
            session_name: Browser session id for domain throttle
            
        Returns:
            Dictionary with 'url' and 'response' (DOM content) keys
        """
        page = None
        try:
            await wait_before_request(session_name, url)
            # Create new page from the shared context
            page = await context.new_page()
            await page.goto(url, wait_until=wait_mode)
            
            # Extract DOM content
            content = await page.content()
            final_url = page.url
            
            logger.info("Webpage loaded successfully", url=final_url, node_id=self.node_config.id)
            
            return {
                "url": final_url,
                "response": content
            }
            
        except Exception as e:
            logger.error("Failed to load webpage", url=url, error=str(e), node_id=self.node_config.id)
            # Return error info instead of raising
            return {
                "url": url,
                "response": None,
                "error": str(e)
            }
        finally:
            # Always close the page to free resources
            if page:
                try:
                    await page.close()
                    logger.debug("Page closed", url=url, node_id=self.node_config.id)
                except Exception as close_error:
                    logger.warning("Error closing page", url=url, error=str(close_error), node_id=self.node_config.id)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Load multiple webpages using Playwright in parallel.

        Inputs:
            node_data.data["urls"]: List of URLs to load (optional).
            node_data.data["url"]: Single URL to load (optional, backward compatibility).

        Form Config:
            urls: URLs to load (newline-separated string or Jinja template like {{ data.urls }}).
            session_name: Name of the persistent context session.
            wait_mode: Wait strategy ('load', 'domcontentloaded', or 'networkidle').
        """
        # Get configuration from form (rendered values)
        session_name = self.form.cleaned_data.get("session_name", "default")
        wait_mode = self.form.cleaned_data.get("wait_mode", "load")  # Default to 'load'

        # Extract URLs from form or input data
        urls = self._extract_urls(node_data)

        logger.info(
            "Loading webpages",
            url_count=len(urls),
            session=session_name,
            wait_mode=wait_mode,
            node_id=self.node_config.id,
        )

        # Get context ONCE before parallel loads to avoid race condition
        # This ensures all pages are created from the same context
        context = await self.browser_manager.get_context(session_name)

        # Load all URLs in parallel using the shared context
        tasks = [
            self._load_single_url(url, context, wait_mode, session_name)
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
                    "Unexpected error loading URL",
                    url=urls[i],
                    error=str(result),
                    node_id=self.node_config.id
                )
                formatted_results.append({
                    "url": urls[i],
                    "response": None,
                    "error": str(result)
                })
            else:
                # Result is a dict from _load_single_url
                formatted_results.append(result)
        
        # Filter out error entries if needed (or keep them for debugging)
        # For now, we'll keep all results including errors
        
        logger.info(
            "All webpages loaded",
            total=len(formatted_results),
            successful=sum(1 for r in formatted_results if r.get("response") is not None),
            failed=sum(1 for r in formatted_results if r.get("error") is not None),
            node_id=self.node_config.id
        )
        
        # Store results in the requested format: [{url: str, response: str}]
        output_key = self.get_unique_output_key(node_data, "webpage_loader")
        node_data.data[output_key] = formatted_results

        return node_data
