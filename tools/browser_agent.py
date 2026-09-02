"""Browser Agent - Playwright web control."""


class BrowserAgent:
    """Async browser automation. Use within asyncio."""

    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None

    async def start(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def goto(self, url):
        if not self.page:
            await self.start()
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await self.page.title()

    async def get_text(self):
        if not self.page:
            return ""
        return await self.page.evaluate("() => document.body.innerText")

    async def click(self, selector):
        await self.page.click(selector, timeout=10000)

    async def fill(self, selector, value):
        await self.page.fill(selector, value)

    async def screenshot(self, path="screenshot.png"):
        await self.page.screenshot(path=path, full_page=True)
        return path

    async def search_web(self, query, max_chars=3000):
        from urllib.parse import quote
        await self.goto(f"https://duckduckgo.com/?q={quote(query)}")
        await self.page.wait_for_timeout(1500)
        text = await self.get_text()
        return text[:max_chars]

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
