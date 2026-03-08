# async playwright script navigate to google.com and wait for close event timeout 0
import asyncio
import logging
import sys
from pathlib import Path

_test_dir = Path(__file__).resolve().parent
_automation_dir = _test_dir.parent.parent  # automation dir so linkedin is a top-level package
sys.path.insert(0, str(_automation_dir))
sys.path.insert(0, str(_test_dir))
from rich.logging import RichHandler

handler = RichHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logging.basicConfig(level=logging.DEBUG, handlers=[handler])
logger = logging.getLogger(__name__)

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from linkedin.page.profile_page.actions import ProfilePageAction

CHROME_PROFILE = Path("/home/roshan-yadav/Desktop/TheOneEye/backend/core/Node/Nodes/Browser/automation/linkedin/test/data/RoshanYadavOnWorkProfile")

chromium_args_reason = {
    "--disable-blink-features=AutomationControlled":
        "Disables the Blink 'AutomationControlled' feature, preventing Chromium from setting navigator.webdriver=true and exposing WebDriver-related automation markers in the JavaScript runtime.",

    "--disable-background-timer-throttling":
        "Prevents Chromium from throttling JavaScript timers (setTimeout, setInterval, requestAnimationFrame) in background tabs, allowing normal timer execution frequency.",

    "--disable-backgrounding-occluded-windows":
        "Stops Chromium from marking occluded or minimized windows as backgrounded, preventing reduced resource allocation due to window visibility state.",

    "--disable-renderer-backgrounding":
        "Prevents lowering of renderer process CPU scheduling priority when a tab is in the background, keeping it at normal foreground priority.",

    "--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,PageLifecycleFreeze":
        "Disables native window occlusion, intensive wake-up throttling, and Page Lifecycle freeze so background/occluded tabs are not throttled or frozen."
}

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE,
            headless=False,
            args=list(chromium_args_reason.keys()),
            viewport={"width": 1920, "height": 1080},
        )

        page = await context.new_page()
        profile_url = "https://www.linkedin.com/in/patricia-nittel-mha/"
        logger.info("Navigating to profile: %s", profile_url)
        await page.goto(profile_url, wait_until="load")
        page_action = ProfilePageAction(page)
        await page.wait_for_timeout(5000)
        logger.info("Running follow_profile")
        await page_action.follow_profile()
        logger.info("Running unfollow_profile")
        await page_action.unfollow_profile()
        logger.info("Running send_connection_request")
        await page_action.send_connection_request()
        logger.info("Running withdraw_connection_request")
        await page_action.withdraw_connection_request()
        await context.wait_for_event("close",timeout=0)
        await context.close()


asyncio.run(main())
