from linkedin.actions.LinkedInBaseAction import LinkedInBaseAtomicAction
from playwright.async_api import Page


class ClickOnMoreButton(LinkedInBaseAtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)

    async def perform_action(self):
        if not await self.profile.more_menu_dialog().is_visible():
            await self.profile.more_menu_button().click()
            await self.profile.more_menu_dialog().wait_for(state="visible")

        
    async def verify_action(self)->bool:
        if await self.profile.more_menu_dialog().is_visible():
            return True
        return False