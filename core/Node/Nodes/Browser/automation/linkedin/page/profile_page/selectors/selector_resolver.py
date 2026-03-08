"""Selector resolver for LinkedIn profile page."""
from playwright.async_api import Page, Locator

from core.selector_resolver import SelectorResolver

from .selector_keys import ProfilePageKey
from .selector_registry import PROFILE_PAGE_SELECTORS


class LinkedInProfilePageSelectors(SelectorResolver):
    """
    Selector resolver for LinkedIn profile pages.

    Usage:
        selectors = LinkedInProfilePageSelectors(page)
        connect_btn = selectors.connect_button()
        await connect_btn.click()

    The get() method is also available for less common selectors:
        selectors.get(ProfilePageKey.REMOVE_CONNECTION_BUTTON)
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page, PROFILE_PAGE_SELECTORS)

    def activity_section_text(self) -> Locator:
        return self.get(ProfilePageKey.ACTIVITY_SECTION_TEXT)

    def connect_button(self) -> Locator:
        return self.get(ProfilePageKey.CONNECT_BUTTON)

    def pending_button(self) -> Locator:
        return self.get(ProfilePageKey.PENDING_BUTTON)

    def message_button(self) -> Locator:
        return self.get(ProfilePageKey.MESSAGE_BUTTON)

    def more_menu_button(self) -> Locator:
        return self.get(ProfilePageKey.MORE_MENU_BUTTON)

    def more_menu_dialog(self) -> Locator:
        return self.get(ProfilePageKey.MORE_MENU_DIALOG)

    def follow_button(self) -> Locator:
        return self.get(ProfilePageKey.FOLLOW_BUTTON)

    def unfollow_button(self) -> Locator:
        return self.get(ProfilePageKey.UNFOLLOW_BUTTON)

    def dialog(self) -> Locator:
        return self.get(ProfilePageKey.DIALOG).first

    def add_note_button(self) -> Locator:
        return self.get(ProfilePageKey.ADD_NOTE_BUTTON)

    def send_without_note_button(self) -> Locator:
        return self.get(ProfilePageKey.SEND_WITHOUT_NOTE_BUTTON)

    def send_button(self) -> Locator:
        return self.get(ProfilePageKey.SEND_BUTTON)

    def add_note_input(self) -> Locator:
        return self.get(ProfilePageKey.ADD_NOTE_INPUT)

    def withdraw_button(self) -> Locator:
        return self.get(ProfilePageKey.WITHDRAW_BUTTON)

    def dialog_unfollow_button(self) -> Locator:
        return self.get(ProfilePageKey.DIALOG_UNFOLLOW_BUTTON)
