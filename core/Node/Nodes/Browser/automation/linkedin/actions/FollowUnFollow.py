import logging

from linkedin.actions.LinkedInBaseAction import (
    LinkedInBaseAtomicAction,
    LinkedInBaseMolecularAction,
)
from linkedin.actions.ClickOnMoreButtonAction import ClickOnMoreButton
from linkedin.actions.utils import human_wait
from linkedin.enums.Status import FollowingStatus
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class FollowProfile(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        action = await ClickOnMoreButton(self.page).accomplish()
        if not action.accomplished:
            logger.warning("Action %s failed", action.__class__.__name__)
            return

        following_status = await self._get_following_status()
        if following_status == FollowingStatus.NOT_FOLLOWING:
            await self.profile.follow_button().click()
            await self.profile.unfollow_button().wait_for(state="visible")
        else:
            logger.info("Already following this profile")

    async def verify_action(self)->bool:
        if await self.profile.unfollow_button().is_visible():
            return True
        return False

class ClickOnUnfollowButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.unfollow_button().click()
        await self.profile.dialog_unfollow_button().wait_for(state="visible")
    
    async def verify_action(self)->bool:
        if await self.profile.dialog_unfollow_button().is_visible():
            return True
        return False

class ClickOnDialogUnfollowButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.dialog_unfollow_button().click()
        await self.profile.dialog_unfollow_button().wait_for(state="hidden")
    
    async def verify_action(self)->bool:
        if not await self.profile.dialog_unfollow_button().is_visible():
            return True
        return False

class UnfollowProfile(LinkedInBaseMolecularAction):
    def __init__(self, page: Page):
        super().__init__(page)

        self.chain_of_actions = [
            ClickOnMoreButton(self.page), 
            ClickOnUnfollowButton(self.page), 
            ClickOnDialogUnfollowButton(self.page)
        ]
    
    async def perform_action(self):
        following_status = await self._get_following_status()
        if following_status == FollowingStatus.FOLLOWING:
            self._accomplished = await self.execute_chain_of_actions()
        else:
            logger.info("Already not following this profile")

    async def verify_action(self)->bool:
        if not await self.profile.unfollow_button().is_visible():
            return True
        return False