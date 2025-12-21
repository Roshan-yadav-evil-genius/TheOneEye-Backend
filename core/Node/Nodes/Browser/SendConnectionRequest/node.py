"""
SendConnectionRequest Node

Single Responsibility: Send LinkedIn connection requests via browser automation.
"""

from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form.Core.BaseForm import BaseForm
from .form import SendConnectionRequestForm
from .._shared.BrowserManager import BrowserManager
from ..automation.linkedin.profile_page import ProfilePage

logger = structlog.get_logger(__name__)


class SendConnectionRequest(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "linkedin-send-connection-request"

    def get_form(self) -> Optional[BaseForm]:
        return SendConnectionRequestForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def setup(self):
        """Initialize BrowserManager connection."""
        self.browser_manager = BrowserManager()
        await self.browser_manager.initialize(headless=False)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Send connection request and/or follow a LinkedIn profile.

        Form Config:
            session_name: Name of the persistent browser context/session.
            profile_url: LinkedIn profile URL (optional, uses current page if empty).
            send_connection_request: Whether to send a connection request.
            follow: Whether to follow the profile.
        """
        session_name = self.form.cleaned_data.get("session_name", "default")
        profile_url = self.form.cleaned_data.get("profile_url", "").strip()
        send_request = self.form.cleaned_data.get("send_connection_request", True)
        follow_profile = self.form.cleaned_data.get("follow", False)

        logger.info(
            "Starting LinkedIn profile actions",
            session=session_name,
            profile_url=profile_url or "(current page)",
            send_request=send_request,
            follow=follow_profile,
            node_id=self.node_config.id,
        )

        try:
            # Get browser context
            context = await self.browser_manager.get_context(session_name)
            page = await self.browser_manager.get_or_create_page(context, profile_url,wait_strategy="load")

            connection_status = None
            following_status = None
            
            profile_page = ProfilePage(page, profile_url)
            await profile_page.load()
            # Perform actions based on form configuration
            if send_request:
                await profile_page.send_connection_request()
                connection_status = await profile_page._get_connection_status()


            if follow_profile:
                await profile_page.follow_profile()
                following_status = await profile_page._get_following_status()
            
            final_data = {
                "connection_request_status": connection_status.value if connection_status else None,
                "follow_status": following_status.value if following_status else None,
                "profile_url": profile_url,
            }
            output_key = self.get_unique_output_key(node_data, "send_connection_request")
            node_data.data[output_key] = final_data

            return node_data

        except Exception as e:
            logger.error(
                "Failed to perform LinkedIn profile actions",
                url=profile_url,
                error=str(e),
            )
            raise e

