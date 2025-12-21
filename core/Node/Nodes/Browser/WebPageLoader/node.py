"""
WebPageLoader Node

Single Responsibility: Load webpages using Playwright browser automation.
"""

from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form.Core.BaseForm import BaseForm
from .form import WebPageLoaderForm
from .._shared.BrowserManager import BrowserManager

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

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Load a webpage using Playwright.

        Inputs:
            node_data.data["url"]: The URL to load.

        Form Config:
            session_name: Name of the persistent context session.
            wait_mode: Wait strategy ('load' or 'networkidle').
        """
        # Get configuration from form (rendered values)


        session_name = self.form.cleaned_data.get("session_name", "default")
        wait_mode = self.form.cleaned_data.get("wait_mode", "load")  # Default to 'load'

        # Get URL: Check form first, then input data
        url = self.form.cleaned_data.get("url")

        logger.info(
            "Loading webpage",
            url=url,
            session=session_name,
            wait_mode=wait_mode,
            node_id=self.node_config.id,
        )

        try:
            # Get context (creates if doesn't exist)
            context = await self.browser_manager.get_context(session_name)

            # Pass wait_mode to navigation
            page = await self.browser_manager.get_or_create_page(
                context, 
                url, 
                wait_strategy=wait_mode
            )

            # (Redundant waits removed as goto handles it via wait_strategy)

            await page.wait_for_timeout(10000)
            
            # Extract basic info
            title = await page.title()
            content = await page.content()

            logger.info("Webpage loaded", title=title, url=page.url)

            final_data = {
                "url": page.url,
                "title": title,
                "content": content,
                "session_name": session_name,
            }
            output_key = self.get_unique_output_key(node_data, "webpage_loader")
            node_data.data[output_key] = final_data

            return node_data

        except Exception as e:
            logger.error("Failed to load webpage", url=url, error=str(e))
            raise e

