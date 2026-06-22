import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

# === CONFIGURATION ===
# Replace with your actual cookies (export from browser dev tools)
# Key cookies for Facebook: c_user, xs, fr, datr, etc.
COOKIES_FILE = "facebook_cookies.json"

# Mobile device to emulate (Android-like)
DEVICE = {
    "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    "viewport": {"width": 412, "height": 915},
    "device_scale_factor": 2.75,
    "is_mobile": True,
    "has_touch": True,
    "default_browser_type": "chromium"
}

async def save_cookies(context: BrowserContext, filepath: str = COOKIES_FILE):
    """Save cookies after manual login"""
    cookies = await context.cookies()
    Path(filepath).write_text(json.dumps(cookies, indent=2), encoding="utf-8")
    print(f"Saved {len(cookies)} cookies to {filepath}")

async def load_cookies(context: BrowserContext, filepath: str = COOKIES_FILE):
    """Load cookies into context"""
    if Path(filepath).exists():
        cookies = json.loads(Path(filepath).read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        print(f"Loaded {len(cookies)} cookies")
        return True
    return False

async def is_logged_in(page):
    """Basic check if logged into Facebook"""
    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
    try:
        # Look for profile or home indicators
        await page.wait_for_selector('div[role="banner"]', timeout=10000)  # Top nav
        # Or check for your name / feed
        if await page.locator("text=What's on your mind?").count() > 0 or "facebook.com/home" in page.url:
            return True
    except:
        pass
    return False

async def main():
    async with async_playwright() as p:
        # Launch with stealth-friendly args + mobile emulation
        browser = await p.chromium.launch(
            headless=False,  # Set True later; headful is safer for login
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
                "--disable-extensions",
                "--disable-plugins",
            ]
        )

        context = await browser.new_context(
            **DEVICE,
            locale="en-US",
            timezone_id="Asia/Karachi",  # Adjust to your timezone
            # permissions=["geolocation", "notifications"]
        )

        # Extra stealth patches
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = { runtime: {}, loadTimes: () => ({}) };
            Object.defineProperty(screen, 'availWidth', {get: () => 412});
        """)

        page = await context.new_page()

        # Try loading cookies
        cookies_loaded = await load_cookies(context)

        if not cookies_loaded or not await is_logged_in(page):
            print("Cookies invalid or expired. Please login manually.")
            await page.goto("https://www.facebook.com/")
            print("Login manually in the browser window...")
            print("After successful login, the script will save cookies.")
            
            # Wait for user to login
            await asyncio.sleep(60)  # Adjust time as needed, or implement better wait
            
            if await is_logged_in(page):
                await save_cookies(context)
                print("Login successful! Cookies saved.")
            else:
                print("Login failed or timed out.")
                await browser.close()
                return
        else:
            print("Successfully logged in with cookies!")

        # Example: Go to your profile or perform actions
        await page.goto("https://www.facebook.com/me", wait_until="networkidle")
        await asyncio.sleep(5)  # Simulate human pause

        # Add your automation here (post, scrape, etc.)
        # Be careful - Facebook bans automation aggressively

        # Keep browser open or close
        # await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
