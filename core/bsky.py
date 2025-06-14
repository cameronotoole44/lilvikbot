import os
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from atproto import Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILTER_DIR = os.path.join(BASE_DIR, "..", "filters")
LOG_FILE = os.path.join(BASE_DIR, "..", "bsky_posts.log")
STATIC_POSTS = os.path.join(FILTER_DIR, "static_posts.txt")

load_dotenv()

BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

# forbidden words
def load_forbidden_words(filename: str) -> set:
    filepath = os.path.join(FILTER_DIR, filename)
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())

HARD_BLOCK = load_forbidden_words("hard_block.txt")
SOFT_BLOCK = load_forbidden_words("soft_block.txt")
SPAM_BLOCK = load_forbidden_words("spam_block.txt")

# filters
def is_safe_bsky(text: str) -> bool:
    lower = text.lower()
    return (
        not any(bad in lower for bad in HARD_BLOCK.union(SOFT_BLOCK)) and
        not any(spam in lower for spam in SPAM_BLOCK)
    )

# logging
def log_event(filename, content):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n")

# no reposts
def load_post_history(filename: str) -> set:
    if not os.path.exists(filename):
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        return set(line.split("] ", 1)[1].strip() for line in f if "] " in line)

# poster class
class LilVikSkyPoster:
    def __init__(self):
        self.client = Client()
        self.posted_set = load_post_history(LOG_FILE)

    async def login(self):
        await asyncio.to_thread(self.client.login, BSKY_HANDLE, BSKY_PASSWORD)
        print(f"[BLSKY] Logged in as @{BSKY_HANDLE}")

    def get_valid_message(self) -> str | None:
        if not os.path.exists(STATIC_POSTS):
            print("[BLSKY] No static_posts.txt found.")
            return None

        with open(STATIC_POSTS, "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]

        random.shuffle(messages)

        for msg in messages:
            if msg not in self.posted_set and is_safe_bsky(msg):
                return msg
        return None

    async def post_loop(self):
        while True:
            await self.login()
            msg = self.get_valid_message()
            if msg:
                try:
                    self.client.send_post(text=msg)
                    print(f"[BLSKY] Posted: {msg}")
                    log_event(LOG_FILE, msg)
                    self.posted_set.add(msg)
                except Exception as e:
                    print(f"[BLSKY] Failed to post: {e}")
            else:
                print("[BLSKY] No new safe messages found.")

            delay = random.randint(4 * 3600, 8 * 3600)
            print(f"[BLSKY] Sleeping for {delay // 60} minutes.")
            await asyncio.sleep(delay)

if __name__ == "__main__":
    poster = LilVikSkyPoster()
    asyncio.run(poster.post_loop())
