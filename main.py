import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_TXT = "facebook_cookies.txt"

def load_netscape_cookies(txt_file: str):
    """Directly parse Netscape .txt cookies for Playwright"""
    cookies = []
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Split by whitespace (handles tabs or spaces)
            parts = line.split()
            if len(parts) < 7:
                continue
                
            domain = parts[0]
            path = parts[2]
            secure = parts[3].upper() == 'TRUE'
            expires = int(parts[4]) if parts[4].isdigit() else None
            name = parts[5]
            value = parts[6]
            
            cookie = {
                "name": name,
                "value": value,
                "domain": domain if domain.startswith('.') else f".{domain}",
                "path": path,
                "secure": secure,
                "httpOnly": True,
                "sameSite": "None" if secure else "Lax"
            }
            
            if expires is not None:
                cookie["expires"] = expires
                
            cookies.append(cookie)
    
    print(f"✅ Loaded {len(cookies)} cookies from {txt_file}")
    return cookies


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process"
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

        # Load cookies directly from .txt
        if Path(COOKIES_TXT).exists():
            cookies_list = load_netscape_cookies(COOKIES_TXT)
            await context.add_cookies(cookies_list)
        else:
            print(f"❌ Error: {COOKIES_TXT} not found!")
            await browser.close()
            return

        page = await context.new_page()

        print("🌐 Navigating to Facebook...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(7)

        # Check if logged in
        logged_in = False
        try:
            if await page.locator("text=What's on your mind?").count() > 0:
                logged_in = True
        except:
            pass

        if logged_in:
            print("✅ Successfully logged in using cookies!")
        else:
            print("⚠️  Could not confirm login. Cookies may be expired or invalid.")

        # Go to profile and take screenshot
        await page.goto("https://www.facebook.com/me", wait_until="networkidle", timeout=30000)
        await page.screenshot(path="facebook_profile.png")
        print("📸 Screenshot saved: facebook_profile.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
