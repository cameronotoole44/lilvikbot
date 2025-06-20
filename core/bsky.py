import os
import random
import asyncio
import markovify
from datetime import datetime
from dotenv import load_dotenv
from atproto import Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILTER_DIR = os.path.join(BASE_DIR, "..", "filters")
LOG_FILE = os.path.join(BASE_DIR, "..", "bsky_posts.log")
LEARNED_LOG = os.path.join(BASE_DIR, "learned.log")

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

# markov loader
def build_markov_model() -> markovify.NewlineText | None:
    print(f"[DEBUG] Looking for learned.log at: {LEARNED_LOG}")
    if not os.path.exists(LEARNED_LOG):
        print("[MODEL] learned.log not found.")
        return None
    lines = []
    with open(LEARNED_LOG, "r", encoding="utf-8") as f:
        for line in f:
            if "] " in line:
                content = line.split("] ", 1)[1].strip()
                if len(content.split()) >= 4:
                    lines.append(content)
    print(f"[MODEL] Using {len(lines)} valid lines.")
    if not lines:
        return None
    return markovify.NewlineText("\n".join(lines), state_size=2)

# poster class
class LilVikSkyPoster:
    def __init__(self):
        self.client = Client()
        self.posted_set = load_post_history(LOG_FILE)
        self.model = build_markov_model()

    async def login(self):
        await asyncio.to_thread(self.client.login, BSKY_HANDLE, BSKY_PASSWORD)
        print(f"[BLSKY] Logged in as @{BSKY_HANDLE}")

    def get_valid_markov(self) -> str | None:
        if not self.model:
            print("[MODEL] No model loaded.")
            return None
        for _ in range(5):
            candidate = self.model.make_short_sentence(300, tries=100)
            print(f"[TRY] {candidate}")
            if not candidate:
                continue
            if candidate in self.posted_set:
                print(f"[SKIP] Already posted: {candidate}")
                continue
            if not is_safe_bsky(candidate):
                print(f"[BLOCKED] Filtered out: {candidate}")
                continue
            return candidate
        return None

    async def post_loop(self):
        while True:
            await self.login()

            msg = None
            for attempt in range(5):
                candidate = self.get_valid_markov()
                if not candidate:
                    break
                print(f"\n[PREVIEW] Generated: {candidate}")
                confirm = input("Post this? [Y/n]: ").strip().lower()
                if confirm in ("", "y", "yes"):
                    msg = candidate
                    break
                else:
                    print("[INFO] Skipping. Trying again...\n")

            if msg:
                try:
                    self.client.send_post(text=msg)
                    print(f"[BLSKY] Posted: {msg}")
                    log_event(LOG_FILE, msg)
                    self.posted_set.add(msg)
                    print("[LOGGED] Post saved to bsky_posts.log")
                except Exception as e:
                    print(f"[BLSKY] Failed to post: {e}")
            else:
                print("[BLSKY] No new Markov messages approved. Skipping post.")

            delay = random.randint(2 * 3600, 4 * 3600)
            print(f"[BLSKY] Sleeping for {delay // 60} minutes.")
            await asyncio.sleep(delay)

if __name__ == "__main__":
    poster = LilVikSkyPoster()
    asyncio.run(poster.post_loop())
