import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = "facebook_cookies.json"

async def main():
    async with async_playwright() as p:
        # === HEADLESS MODE FOR GITHUB ACTIONS ===
        browser = await p.chromium.launch(
            headless=True,   # MUST be True in CI
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
            device_scale_factor=2.75,
            is_mobile=True,
            has_touch=True,
            locale="en-US",
            timezone_id="Asia/Karachi",
        )

        # Stealth
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        # Load cookies
        if Path(COOKIES_FILE).exists():
            cookies = json.loads(Path(COOKIES_FILE).read_text(encoding="utf-8"))
            await context.add_cookies(cookies)
            print(f"✅ Loaded {len(cookies)} cookies")
        else:
            print("❌ facebook_cookies.json not found!")
            await browser.close()
            return

        page = await context.new_page()

        # Test login
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(6)

        logged_in = False
        try:
            if await page.locator("text=What's on your mind?").count() > 0:
                logged_in = True
        except:
            pass

        if logged_in:
            print("✅ Successfully logged in with cookies!")
        else:
            print("⚠️ Could not confirm login. Cookies may be expired.")

        # Example action
        await page.goto("https://www.facebook.com/me", wait_until="networkidle", timeout=30000)
        await page.screenshot(path="facebook_profile.png")
        print("📸 Screenshot saved: facebook_profile.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
