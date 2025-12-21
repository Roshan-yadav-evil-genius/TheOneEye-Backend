from .keys.profile_page import ProfilePageKey

PROFILE_PAGE_SELECTORS = {
    # Main Profile Action Bar (Root element - no parent)
    ProfilePageKey.PROFILE_CARD: {
        "selectors": [
            "(//section[contains(@class,'artdeco-card')])[1]//ul[.//li[contains(normalize-space(.),'connections')]]/following-sibling::*[1]",
        ],
        "parent": None
    },
    
    # Buttons scoped to PROFILE_CARD
    ProfilePageKey.CONNECT_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Connect']]",
            "//div[@role='button'][.//span[text()='Connect']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    ProfilePageKey.PENDING_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Pending']]",
            "//div[@role='button'][.//span[text()='Pending']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    ProfilePageKey.MESSAGE_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Message']]",
            "//div[@role='button'][.//span[text()='Message']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    ProfilePageKey.MORE_MENU_BUTTON: {
        "selectors": [
            "//button[.//span[text()='More']]",
            "//button[@aria-label='More actions']",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    
    # Global buttons (no parent - searched from page root)
    ProfilePageKey.FOLLOW_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Follow']]",
            "//div[@role='button'][.//span[text()='Follow']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    ProfilePageKey.UNFOLLOW_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Unfollow']]",
            "//div[@role='button'][.//span[text()='Unfollow']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },
    ProfilePageKey.REMOVE_CONNECTION_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Remove connection']]",
            "//div[@role='button'][.//span[text()='Remove connection']]",
        ],
        "parent": ProfilePageKey.PROFILE_CARD
    },

    # Dialogs (global)
    ProfilePageKey.DIALOG: {
        "selectors": [
            "//div[@role='dialog']",
            "//div[@role='alertdialog']",
        ],
        "parent": None
    },
    ProfilePageKey.WITHDRAW_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Withdraw']]",
        ],
        "parent": ProfilePageKey.DIALOG
    },

    ProfilePageKey.DIALOG_UNFOLLOW_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Unfollow']]",
            "//div[@role='button'][.//span[text()='Unfollow']]",
        ],
        "parent": ProfilePageKey.DIALOG
    },
    
    # Dialog Actions (scoped to DIALOG)
    ProfilePageKey.ADD_NOTE_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Add a note']]",
        ],
        "parent": ProfilePageKey.DIALOG
    },
    ProfilePageKey.SEND_WITHOUT_NOTE_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Send without a note']]",
        ],
        "parent": ProfilePageKey.DIALOG
    },
    ProfilePageKey.SEND_BUTTON: {
        "selectors": [
            "//button[.//span[text()='Send']]",
        ],
        "parent": ProfilePageKey.DIALOG
    },
    ProfilePageKey.MESSAGE_INPUT: {
        "selectors": [
            "//textarea[@name='message']",
        ],
        "parent": ProfilePageKey.DIALOG
    }
}
