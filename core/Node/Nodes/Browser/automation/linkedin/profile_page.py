import logging
from playwright.sync_api import Page, Locator
from .selectors.profile_page import LinkedInProfilePageSelectors
from urllib.parse import urlparse
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    PENDING = "pending"


class FollowingStatus(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWING = "following"


class ProfilePage:
    def __init__(self, page: Page, profile_url: str):
        self.page = page

        if not self._is_valid_linkedin_profile_url(profile_url):
            logger.error("Invalid LinkedIn profile URL: %s", profile_url)
            raise ValueError("Invalid LinkedIn profile URL.")

        # Normalize URL to use https and www prefix
        self.profile_url = self._normalize_linkedin_url(profile_url)
        self.profile = LinkedInProfilePageSelectors(self.page)
        logger.debug("Initialized ProfilePage for: %s", self.profile_url)

    # ─────────────────────────────────────────────────────────────
    # Public Methods
    # ─────────────────────────────────────────────────────────────

    def load(self):
        logger.debug("Loading profile page: %s", self.profile_url)
        self.page.goto(self.profile_url, wait_until="load")
        logger.info("Profile page loaded: %s", self.profile_url)

    def follow_profile(self):
        following_status = self._get_following_status()
        logger.debug("Current following status: %s", following_status)

        if following_status == FollowingStatus.NOT_FOLLOWING:
            logger.info("Following profile")
            follow_btn = self.profile.follow_button()
            self._click_or_expand_more_menu(follow_btn, "Follow")
        else:
            logger.info("Already following this profile")

    def unfollow_profile(self):
        following_status = self._get_following_status()
        logger.debug("Current following status: %s", following_status)

        if following_status == FollowingStatus.FOLLOWING:
            logger.info("Unfollowing profile")
            unfollow_btn = self.profile.unfollow_button()
            self._click_or_expand_more_menu(unfollow_btn, "Unfollow")

            dialog = self._wait_for_dialog("clicking Unfollow")
            if not dialog:
                return
            confirm_unfollow_btn = self.profile.dialog_unfollow_button()
            if confirm_unfollow_btn.is_visible():
                confirm_unfollow_btn.click()
                logger.info("Profile unfollowed successfully")
        else:
            logger.info("Already not following this profile")

    def send_connection_request(self, note: str = ""):
        connection_status = self._get_connection_status()
        logger.debug("Current connection status: %s", connection_status)

        if connection_status == ConnectionStatus.NOT_CONNECTED:
            logger.info("Sending connection request")
            self._send_connection_request(note)
            logger.info("Connection request sent successfully")
        else:
            logger.info("Cannot send connection request - status is %s", connection_status)

    def withdraw_connection_request(self):
        connection_status = self._get_connection_status()
        logger.debug("Current connection status: %s", connection_status)

        if connection_status != ConnectionStatus.PENDING:
            logger.warning("Cannot withdraw - not in Pending state (current: %s)", connection_status)
            return

        logger.info("Withdrawing connection request")
        pending_btn = self.profile.pending_button()

        if not self._click_or_expand_more_menu(pending_btn, "Pending"):
            return

        dialog = self._wait_for_dialog("clicking Pending")
        if not dialog:
            return

        withdraw_btn = self.profile.withdraw_button()
        if withdraw_btn.is_visible():
            withdraw_btn.click()
            logger.info("Connection request withdrawn successfully")
        else:
            logger.error("Could not find 'Withdraw' button")

    # ─────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────

    def _send_connection_request(self, note: str = ""):
        connect_btn = self.profile.connect_button()

        if not self._click_or_expand_more_menu(connect_btn, "Connect"):
            return

        dialog = self._wait_for_dialog("clicking Connect")
        if not dialog:
            logger.error("Connection dialog did not appear")
            return

        if note:
            logger.debug("Sending connection request with note")
            add_note_btn = self.profile.add_note_button()
            if add_note_btn.is_visible():
                add_note_btn.click()
                self.profile.message_input().fill(note)
                self.profile.send_button().click()
            else:
                logger.warning("'Add a note' button not found")
        else:
            logger.debug("Sending connection request without note")
            send_without_note_btn = self.profile.send_without_note_button()
            if send_without_note_btn.is_visible():
                send_without_note_btn.click()
            else:
                logger.warning("'Send without a note' button not found")

    @staticmethod
    def _is_valid_linkedin_profile_url(profile_url: str) -> bool:
        # EX: https://www.linkedin.com/in/zackspear/
        # Also accepts http:// URLs (will be normalized to https in __init__)

        parsed = urlparse(profile_url)

        # Accept both http and https
        if parsed.scheme not in ("http", "https"):
            return False

        # Accept with or without www prefix
        netloc = parsed.netloc.lower()
        if netloc not in ("www.linkedin.com", "linkedin.com"):
            return False

        paths = [p for p in parsed.path.strip("/").split("/") if p]

        return len(paths) == 2 and paths[0] == "in"
    
    @staticmethod
    def _normalize_linkedin_url(profile_url: str) -> str:
        """Normalize LinkedIn URL to use https and www prefix."""
        parsed = urlparse(profile_url)
        netloc = parsed.netloc.lower()
        
        # Ensure www prefix
        if netloc == "linkedin.com":
            netloc = "www.linkedin.com"
        
        # Rebuild with https
        return f"https://{netloc}{parsed.path}"

    def _click_or_expand_more_menu(self, button: Locator, button_name: str) -> bool:
        """
        Click button directly, or expand More menu first if needed.

        Returns:
            True if button was clicked successfully, False otherwise.
        """
        if button.is_visible():
            logger.debug("Clicking '%s' button", button_name)
            button.click()
            return True

        logger.debug("Button '%s' not visible, expanding More menu", button_name)
        self.profile.more_menu_button().click()

        try:
            button.wait_for(state="visible", timeout=5000)
            button.click()
            logger.debug("Clicked '%s' button from More menu", button_name)
            return True
        except Exception:
            logger.error("Could not find '%s' even in More menu", button_name)
            return False

    def _wait_for_dialog(self, context: str = "action") -> Locator | None:
        """
        Wait for dialog to appear.

        Args:
            context: Description of what triggered the dialog (for error message)

        Returns:
            Dialog locator if found, None otherwise.
        """
        logger.debug("Waiting for dialog after %s", context)
        dialog = self.profile.dialog()
        try:
            dialog.wait_for(state="visible", timeout=5000)
            logger.debug("Dialog appeared successfully")
            return dialog
        except Exception:
            logger.warning("Dialog did not appear after %s", context)
            return None

    def _get_connection_status(self) -> ConnectionStatus:
        if self.profile.connect_button().count():
            return ConnectionStatus.NOT_CONNECTED

        if self.profile.pending_button().count():
            return ConnectionStatus.PENDING

        return ConnectionStatus.CONNECTED

    def _get_following_status(self) -> FollowingStatus:
        if self.profile.follow_button().count():
            return FollowingStatus.NOT_FOLLOWING
        return FollowingStatus.FOLLOWING
