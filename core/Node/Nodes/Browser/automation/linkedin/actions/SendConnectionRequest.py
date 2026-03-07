from linkedin.enums.Status import ConnectionStatus
from .BaseProfilePageAction import BaseProfilePageAction
from playwright.async_api import Page,Locator
from linkedin.selectors.profile_page import LinkedInProfilePageSelectors
import random


async def human_type(locator: Locator, text: str, min_ms: int = 50, max_ms: int = 300):
    for ch in text:
        await locator.type(ch,delay=random.randint(min_ms, max_ms))

class ClickOnMoreButton(BaseProfilePageAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.more_menu_button().click()
        await self.profile.more_menu_dialog().wait_for(state="visible")

        
    async def verify_action(self)->bool:
        if await self.profile.more_menu_dialog().is_visible():
            return True
        return False


class ClickOnConnectButton(BaseProfilePageAction):
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

class ClickOnAddNoteButton(BaseProfilePageAction):
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

class ClickOnSendWithoutNoteButton(BaseProfilePageAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.send_without_note_button().click()
        await self.page.wait_for_timeout(500)


    async def verify_action(self)->bool:
        if not await self.profile.send_without_note_button().is_visible():
            return True
        return False


class FillAddNoteInput(BaseProfilePageAction):
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

class SubmitInvitationNote(BaseProfilePageAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        await self.profile.send_button().click()
        await self.page.wait_for_timeout(500)

    async def verify_action(self)->bool:
        if not await self.profile.send_button().is_visible():
            return True
        return False

class SendConnectionRequest(BaseProfilePageAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.chain_of_actions = [
            ClickOnMoreButton(self.page), 
            ClickOnConnectButton(self.page), 
            # ClickOnSendWithoutNoteButton(self.page)
            ClickOnAddNoteButton(self.page), 
            FillAddNoteInput(self.page, "Hello, I want to connect with you"),
            SubmitInvitationNote(self.page)
            ]

    async def human_wait(self, min_ms=50, max_ms=500):
        delay = random.randint(min_ms, max_ms)
        await self.page.wait_for_timeout(delay)


    async def execute_chain_of_actions(self):
        for action in self.chain_of_actions:
            action = await action.accomplish()
            if not action.accomplished:
                print(f"Action {action.__class__.__name__} failed")
                return
            
            await self.human_wait()


    async def perform_action(self):
        connection_status = await self._get_connection_status()
        print(connection_status.name)
        if connection_status == ConnectionStatus.NOT_CONNECTED:
            await self.execute_chain_of_actions()
        else:
            print("Connection already established")

    async def verify_action(self)->bool:
        pass