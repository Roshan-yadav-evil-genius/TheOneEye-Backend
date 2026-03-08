"""Selector registry for LinkedIn profile page."""
from core.models import SelectorEntry, SelectorRegistry

from .selector_keys import ProfilePageKey

PROFILE_PAGE_SELECTORS: SelectorRegistry[ProfilePageKey] = SelectorRegistry()

# Main Profile Action Bar (Root element - no parent)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.PROFILE_CARD,
        selectors=[
            "(//section[contains(@class,'artdeco-card')])[1]//ul[.//li[contains(normalize-space(.),'connections')]]/following-sibling::*[1]",
        ],
        parent=None,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.ACTIVITY_SECTION_TEXT,
        selectors=[
            "//section[contains(@class,'artdeco-card')]//span[normalize-space()='Activity' and not(contains(@class,'visually-hidden'))]",
        ],
        parent=None,
    )
)
# Buttons scoped to PROFILE_CARD
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.CONNECT_BUTTON,
        selectors=[
            "//button[.//span[text()='Connect']]",
            "//div[@role='button'][.//span[text()='Connect']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.PENDING_BUTTON,
        selectors=[
            "//button[.//span[text()='Pending']]",
            "//div[@role='button'][.//span[text()='Pending']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.MESSAGE_BUTTON,
        selectors=[
            "//button[.//span[text()='Message']]",
            "//div[@role='button'][.//span[text()='Message']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.MORE_MENU_BUTTON,
        selectors=[
            "//button[.//span[text()='More']]",
            "//button[@aria-label='More actions']",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.MORE_MENU_DIALOG,
        selectors=[
            "xpath=./following-sibling::div[1][@aria-hidden='false']",
        ],
        parent=ProfilePageKey.MORE_MENU_BUTTON,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.FOLLOW_BUTTON,
        selectors=[
            "//button[.//span[text()='Follow']]",
            "//div[@role='button'][.//span[text()='Follow']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.UNFOLLOW_BUTTON,
        selectors=[
            "//button[.//span[text()='Unfollow']]",
            "//div[@role='button'][.//span[text()='Unfollow']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.REMOVE_CONNECTION_BUTTON,
        selectors=[
            "//button[.//span[text()='Remove connection']]",
            "//div[@role='button'][.//span[text()='Remove connection']]",
        ],
        parent=ProfilePageKey.PROFILE_CARD,
    )
)
# Dialogs (global)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.DIALOG,
        selectors=[
            "//div[@role='dialog']",
            "//div[@role='alertdialog']",
        ],
        parent=None,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.WITHDRAW_BUTTON,
        selectors=[
            "//button[.//span[text()='Withdraw']]",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.DIALOG_UNFOLLOW_BUTTON,
        selectors=[
            "//button[.//span[text()='Unfollow']]",
            "//div[@role='button'][.//span[text()='Unfollow']]",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
# Dialog Actions (scoped to DIALOG)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.ADD_NOTE_BUTTON,
        selectors=[
            "//button[.//span[text()='Add a note']]",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.SEND_WITHOUT_NOTE_BUTTON,
        selectors=[
            "//button[.//span[text()='Send without a note']]",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.SEND_BUTTON,
        selectors=[
            "//button[.//span[text()='Send']]",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
PROFILE_PAGE_SELECTORS.register(
    SelectorEntry(
        key=ProfilePageKey.ADD_NOTE_INPUT,
        selectors=[
            "//textarea[@name='message']",
        ],
        parent=ProfilePageKey.DIALOG,
    )
)
