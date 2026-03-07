import logging
import random

from linkedin.actions.LinkedInBaseAction import (
    LinkedInBaseAtomicAction,
    LinkedInBaseMolecularAction,
)
from linkedin.actions.ClickOnMoreButtonAction import ClickOnMoreButton
from linkedin.actions.utils import human_type, human_wait
from linkedin.enums.Status import ConnectionStatus
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class ClickOnConnectButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        if await self.profile.connect_button().is_visible():
            await self.profile.connect_button().click()
            await self._wait_for_dialog("clicking Connect")

        
    async def verify_action(self)->bool:
        if await self.profile.dialog().is_visible():
            return True
        return False

class ClickOnAddNoteButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        if await self.profile.dialog().is_visible():
            await self.profile.add_note_button().click()
            await self.profile.add_note_input().wait_for(state="visible")


    async def verify_action(self)->bool:
        if await self.profile.add_note_input().is_visible():
            return True
        return False

class ClickOnSendWithoutNoteButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        try:
            await self.profile.send_without_note_button().click(timeout=10000)
            await self.profile.pending_button().wait_for(state="visible")
        except Exception as e:
            logger.error(e)

    async def verify_action(self)->bool:

        if await self.profile.pending_button().is_visible():
            return True
        return False


class FillAddNoteInput(LinkedInBaseAtomicAction):
    def __init__(self, page: Page, invitation_note:str):
        super().__init__(page)
        self.invitation_note = invitation_note

    async def perform_action(self):
        """Type text with randomized per-keystroke delay to mimic human input."""
        await human_type(self.profile.add_note_input(), self.invitation_note)
        

    async def verify_action(self)->bool:
        if await self.profile.add_note_input().input_value() == self.invitation_note:
            return True
        return False

class SubmitInvitationNote(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.send_button().click()
        await self.page.wait_for_timeout(500)

    async def verify_action(self)->bool:
        if not await self.profile.send_button().is_visible():
            return True
        return False

class SendConnectionRequest(LinkedInBaseMolecularAction):
    def __init__(self, page: Page, invitation_note:str=""):
        super().__init__(page)
        self.invitation_note = invitation_note
        self.send_without_note = [
            ClickOnMoreButton(self.page), 
            ClickOnConnectButton(self.page), 
            ClickOnSendWithoutNoteButton(self.page)
        ]
        self.send_with_note = [
            ClickOnMoreButton(self.page), 
            ClickOnConnectButton(self.page), 
            ClickOnAddNoteButton(self.page), 
            FillAddNoteInput(self.page, self.invitation_note),
            SubmitInvitationNote(self.page)
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

    async def verify_action(self)->bool:
        return self._accomplished

class ClickOnPendingButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.pending_button().click()
        await self.profile.withdraw_button().wait_for(state="visible")

    async def verify_action(self)->bool:
        if await self.profile.withdraw_button().is_visible():
            return True
        return False

class ClickOnWithdrawButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.withdraw_button().click()
        await self.profile.withdraw_button().wait_for(state="hidden")

    async def verify_action(self)->bool:
        if not await self.profile.withdraw_button().is_visible():
            return True
        return False

class WithdrawConnectionRequest(LinkedInBaseMolecularAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.chain_of_actions = [
            ClickOnMoreButton(self.page), 
            ClickOnPendingButton(self.page),
            ClickOnWithdrawButton(self.page)
        ]
    
    async def perform_action(self):
        connection_status = await self._get_connection_status()
        if connection_status == ConnectionStatus.PENDING:
            self._accomplished=await self.execute_chain_of_actions()
        else:
            logger.warning("Failed to withdraw connection request. User is not in pending state")
    
    async def verify_action(self)->bool:
        return self._accomplished