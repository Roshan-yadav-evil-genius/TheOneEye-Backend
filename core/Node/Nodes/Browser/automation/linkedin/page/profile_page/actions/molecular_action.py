"""Molecular actions for LinkedIn profile page."""
import logging

from .base_action import LinkedInBaseMolecularAction
from .profile_state import ConnectionStatus, FollowingStatus
from playwright.async_api import Page

from .atomic_action import (
    ClickOnAddNoteButton,
    ClickOnConnectButton,
    ClickOnDialogUnfollowButton,
    ClickOnMoreButton,
    ClickOnPendingButton,
    ClickOnSendWithoutNoteButton,
    ClickOnUnfollowButton,
    ClickOnWithdrawButton,
    FillAddNoteInput,
    SubmitInvitationNote,
)

logger = logging.getLogger(__name__)


class SendConnectionRequest(LinkedInBaseMolecularAction):
    def __init__(self, page: Page, invitation_note: str = ""):
        super().__init__(page)
        self.invitation_note = invitation_note
        self.send_without_note = [
            ClickOnMoreButton(self.page),
            ClickOnConnectButton(self.page),
            ClickOnSendWithoutNoteButton(self.page),
        ]
        self.send_with_note = [
            ClickOnMoreButton(self.page),
            ClickOnConnectButton(self.page),
            ClickOnAddNoteButton(self.page),
            FillAddNoteInput(self.page, self.invitation_note),
            SubmitInvitationNote(self.page),
        ]
        if self.invitation_note:
            self.chain_of_actions = self.send_with_note
        else:
            self.chain_of_actions = self.send_without_note

    async def perform_action(self):
        connection_status = await self._get_connection_status()
        logger.debug("Connection status: %s", connection_status.name)
        if connection_status == ConnectionStatus.NOT_CONNECTED:
            self._accomplished = await self.execute_chain_of_actions()
        else:
            logger.info("Connection already established")

    async def verify_action(self) -> bool:
        return self._accomplished


class WithdrawConnectionRequest(LinkedInBaseMolecularAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.chain_of_actions = [
            ClickOnMoreButton(self.page),
            ClickOnPendingButton(self.page),
            ClickOnWithdrawButton(self.page),
        ]

    async def perform_action(self):
        connection_status = await self._get_connection_status()
        if connection_status == ConnectionStatus.PENDING:
            self._accomplished = await self.execute_chain_of_actions()
        else:
            logger.warning("Failed to withdraw connection request. User is not in pending state")

    async def verify_action(self) -> bool:
        return self._accomplished


class FollowProfile(LinkedInBaseMolecularAction):
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

    async def verify_action(self) -> bool:
        if await self.profile.unfollow_button().is_visible():
            return True
        return False


class UnfollowProfile(LinkedInBaseMolecularAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.chain_of_actions = [
            ClickOnMoreButton(self.page),
            ClickOnUnfollowButton(self.page),
            ClickOnDialogUnfollowButton(self.page),
        ]

    async def perform_action(self):
        following_status = await self._get_following_status()
        if following_status == FollowingStatus.FOLLOWING:
            self._accomplished = await self.execute_chain_of_actions()
        else:
            logger.info("Already not following this profile")

    async def verify_action(self) -> bool:
        if not await self.profile.unfollow_button().is_visible():
            return True
        return False
