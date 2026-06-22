import os
import pickle
import random
import socket
import time
import uuid
import requests
from http.cookiejar import MozillaCookieJar
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ====================== CONFIG ======================
RUN_TAG = os.getenv("GITHUB_RUN_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
CLAIM_PREFIX = "CLAIMED_"

COOKIE_FILE = "facebook_cookies.txt"          # ← your cookies file
LOOP_INTERVAL_SECONDS = 1860                  # 31 minutes

# Text / Captions
CAPTION_TEMPLATE = """{video_name}

👉 Fuck Me 1-on-1
"""

LINKS = [
    "https://lvx.teentoday.cfd/",
    # Add more links if needed
]

def get_env(name, required=True):
    value = os.getenv(name)
    if value is None:
        if required:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return ""
    return value.strip()

def load_facebook_session():
    """Load Netscape cookies into requests session"""
    session = requests.Session()
    cj = MozillaCookieJar()
    cj.load(COOKIE_FILE, ignore_discard=True, ignore_expires=True)
    session.cookies = cj
    
    # Important headers to look more natural
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session

def get_creds():
    with open("token.pickle", "rb") as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def pick_random_hashtags(filepath="hashtags.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        return ""
    chosen = random.choice(lines)
    return chosen  # keep the #tags as they are

def claim_file(service, file_id, current_name):
    claimed_name = f"{CLAIM_PREFIX}{RUN_TAG}__{current_name}"
    service.files().update(fileId=file_id, body={"name": claimed_name}).execute()
    check = service.files().get(fileId=file_id, fields="id,name").execute()
    if check.get("name") != claimed_name:
        print(f"Lost claim race on {file_id}")
        return None
    return claimed_name

def fetch_latest_video():
    creds = get_creds()
    service = build("drive", "v3", credentials=creds)
    folder_id = get_env("UPLOAD_FOLDER_ID")
    
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        orderBy="createdTime desc",
        pageSize=10
    ).execute()
    
    for file in results.get("files", []):
        mime = file.get("mimeType", "")
        original_name = file["name"]
        
        if original_name.startswith(CLAIM_PREFIX):
            continue
        if not mime.startswith("video/"):
            continue
            
        print(f"Found video: {original_name}")
        claimed_name = claim_file(service, file["id"], original_name)
        if not claimed_name:
            continue
            
        # Download
        request = service.files().get_media(fileId=file["id"])
        local_path = f"/tmp/{original_name}"
        with open(local_path, "wb") as f:
            f.write(request.execute())
            
        file["claimed_name"] = claimed_name
        file["original_name"] = original_name
        return file, local_path
    
    print("No unclaimed video found.")
    return None, None

def release_claim(file_id, original_name):
    try:
        creds = get_creds()
        service = build("drive", "v3", credentials=creds)
        service.files().update(fileId=file_id, body={"name": original_name}).execute()
        print(f"Released claim on {original_name}")
    except Exception as e:
        print(f"Failed to release claim: {e}")

def move_file(file_id, restore_name=None):
    creds = get_creds()
    service = build("drive", "v3", credentials=creds)
    upload_id = get_env("UPLOAD_FOLDER_ID")
    processed_id = get_env("PROCESSED_FOLDER_ID")
    
    body = {"name": restore_name} if restore_name else {}
    service.files().update(
        fileId=file_id,
        addParents=processed_id,
        removeParents=upload_id,
        body=body
    ).execute()
    print("Moved to processed folder.")

def post_to_facebook(session, video_path, video_name):
    hashtags = pick_random_hashtags()
    caption = CAPTION_TEMPLATE.format(video_name=video_name) + "\n" + hashtags
    
    # This is the simplest attempt. Facebook blocks many cookie-based uploads now.
    # For reliable posting, you should use Graph API + Page Access Token instead.
    files = {
        'source': open(video_path, 'rb'),
        'caption': (None, caption),
        'description': (None, caption),
    }
    
    # Try posting to your profile (me/videos)
    r = session.post("https://graph.facebook.com/me/videos", files=files)
    
    print(f"Facebook response: {r.status_code}")
    print(r.text[:500])
    
    if r.status_code in (200, 202):
        print("✅ Video posted successfully to Facebook!")
        return True
    else:
        raise Exception(f"Facebook post failed: {r.status_code} - {r.text[:300]}")

def run_once():
    session = load_facebook_session()
    file, local_path = fetch_latest_video()
    if not file:
        return
    
    original_name = file.get("original_name", file["name"])
    try:
        post_to_facebook(session, local_path, original_name)
        move_file(file["id"], restore_name=original_name)
    except Exception as e:
        print(f"Error during post: {e}")
        release_claim(file["id"], original_name)
        raise
    finally:
        try:
            os.remove(local_path)
        except:
            pass

def main():
    print(f"Starting Facebook poster loop (every {LOOP_INTERVAL_SECONDS}s)")
    while True:
        cycle_start = time.time()
        try:
            run_once()
        except Exception as e:
            print(f"Cycle error: {e}")
        elapsed = time.time() - cycle_start
        sleep_for = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        print(f"Cycle done in {elapsed:.1f}s. Sleeping {sleep_for:.1f}s...")
        time.sleep(sleep_for)

if __name__ == "__main__":
    main()
