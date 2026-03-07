from enum import Enum

class ProfilePageKey(Enum):
    # Main Sections
    PROFILE_CARD = "action_bar"
    
    # Buttons
    CONNECT_BUTTON = "connect_button"
    PENDING_BUTTON = "pending_button"
    MESSAGE_BUTTON = "message_button"
    FOLLOW_BUTTON = "follow_button"
    UNFOLLOW_BUTTON = "unfollow_button"
    REMOVE_CONNECTION_BUTTON = "remove_connection_button"
    
    # Menus
    MORE_MENU_BUTTON = "more_menu_trigger"
    MORE_MENU_DIALOG = "more_menu_dialog"
    
    # Dialogs
    DIALOG = "dialog"

    # Connection request dialog
    ADD_NOTE_BUTTON = "add_note_button"
    SEND_WITHOUT_NOTE_BUTTON = "send_without_note_button"

    # Connection request with msg dialog
    ADD_NOTE_INPUT = "add_note_input"
    SEND_BUTTON = "send_button"

    # Withdraw connection request dialog
    WITHDRAW_BUTTON = "withdraw_button"

    # Unfollow confirmation dialog
    DIALOG_UNFOLLOW_BUTTON = "dialog_unfollow_button"
