from playwright.async_api import Page, Locator
from .core.profile_page import PROFILE_PAGE_SELECTORS
from .core.keys.profile_page import ProfilePageKey
from .base_page import BasePage


class LinkedInProfilePageSelectors(BasePage):
    """
    Selector class for LinkedIn profile pages.
    
    Usage:
        selectors = LinkedInProfilePageSelectors(page)
        connect_btn = selectors.connect_button()
        await connect_btn.click()
    
    The get() method is also available for less common selectors:
        selectors.get(ProfilePageKey.REMOVE_CONNECTION_BUTTON)
    """
    
    def __init__(self, page: Page):
        super().__init__(page, PROFILE_PAGE_SELECTORS)

    # ─────────────────────────────────────────────────────────────
    # Connection Status Buttons
    # ─────────────────────────────────────────────────────────────
    
    def connect_button(self) -> Locator:
        """Returns the Connect button locator."""
        return self.get(ProfilePageKey.CONNECT_BUTTON)
    
    def pending_button(self) -> Locator:
        """Returns the Pending button locator."""
        return self.get(ProfilePageKey.PENDING_BUTTON)
    
    def message_button(self) -> Locator:
        """Returns the Message button locator."""
        return self.get(ProfilePageKey.MESSAGE_BUTTON)

    # ─────────────────────────────────────────────────────────────
    # Action Buttons
    # ─────────────────────────────────────────────────────────────
    
    def more_menu_button(self) -> Locator:
        """Returns the More menu trigger button locator."""
        return self.get(ProfilePageKey.MORE_MENU_BUTTON)
    
    def follow_button(self) -> Locator:
        """Returns the Follow button locator."""
        return self.get(ProfilePageKey.FOLLOW_BUTTON)
    
    def unfollow_button(self) -> Locator:
        """Returns the Unfollow button locator."""
        return self.get(ProfilePageKey.UNFOLLOW_BUTTON)

    # ─────────────────────────────────────────────────────────────
    # Dialog & Dialog Actions
    # ─────────────────────────────────────────────────────────────
    
    def dialog(self) -> Locator:
        """Returns the first visible dialog locator."""
        return self.get(ProfilePageKey.DIALOG).first
    
    # ─────────────────────────────────────────────────────────────
    #  Connection Request Dialog Actions
    # ─────────────────────────────────────────────────────────────

    def add_note_button(self) -> Locator:
        """Returns the 'Add a note' button locator."""
        return self.get(ProfilePageKey.ADD_NOTE_BUTTON)
    
    def send_without_note_button(self) -> Locator:
        """Returns the 'Send without a note' button locator."""
        return self.get(ProfilePageKey.SEND_WITHOUT_NOTE_BUTTON)

    # ─────────────────────────────────────────────────────────────
    #  Connection Request with msg Dialog Actions
    # ─────────────────────────────────────────────────────────────

    def send_button(self) -> Locator:
        """Returns the Send button locator."""
        return self.get(ProfilePageKey.SEND_BUTTON)
    
    def message_input(self) -> Locator:
        """Returns the message textarea locator."""
        return self.get(ProfilePageKey.MESSAGE_INPUT)
    
    # ─────────────────────────────────────────────────────────────
    #  Withdraw Connection Request Dialog Actions
    # ─────────────────────────────────────────────────────────────

    def withdraw_button(self) -> Locator:
        """Returns the Withdraw button locator."""
        return self.get(ProfilePageKey.WITHDRAW_BUTTON)

    # ─────────────────────────────────────────────────────────────
    #  Unfollow Dialog Actions
    # ─────────────────────────────────────────────────────────────
    def dialog_unfollow_button(self) -> Locator:
        """Returns the Unfollow button locator within a dialog."""
        return self.get(ProfilePageKey.DIALOG_UNFOLLOW_BUTTON)
