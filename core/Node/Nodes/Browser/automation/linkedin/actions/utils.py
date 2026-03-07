import random
from playwright.async_api import Locator, Page


async def human_type(locator: Locator, text: str, min_ms: int = 50, max_ms: int = 300):
    for ch in text:
        await locator.type(ch,delay=random.randint(min_ms, max_ms))

async def human_wait(page: Page, min_ms: int = 50, max_ms: int = 500):
    delay = random.randint(min_ms, max_ms)
    await page.wait_for_timeout(delay)