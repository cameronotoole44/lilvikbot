import os
import re
import random
import asyncio
import markovify
import twitchio
from twitchio.ext.commands import Bot
from twitchio.ext.routines import routine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

raw_token = os.getenv("TWITCH_OAUTH_TOKEN", "").strip()
TOKEN = raw_token.replace("oauth:", "")
CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip()
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "true").lower() == "true"

# debug prints
# print(f"[DEBUG] twitchio version: {twitchio.__version__}")
# print(f"[DEBUG] using token prefix: {TOKEN[:6]}... (length {len(TOKEN)})")
# print(f"[DEBUG] channel: {CHANNEL}")

MAX_MEMORY = 10000  # cap

# filters
def load_forbidden_words(filename):
    path = os.path.join("filters", filename)
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(
            line.strip().lower()
            for line in f
            if line.strip() and not line.startswith("#")
        )

HARD_BLOCK = load_forbidden_words("hard_block.txt")
SOFT_BLOCK = load_forbidden_words("soft_block.txt")
SPAM_BLOCK = load_forbidden_words("spam_block.txt")
print(f"[FILTER] Loaded {len(HARD_BLOCK)} hard, {len(SOFT_BLOCK)} soft, {len(SPAM_BLOCK)} spam blocks")

def is_learnable(text: str) -> bool:
    lower = text.lower()
    return not any(bad in lower for bad in HARD_BLOCK)

def is_speakable(text: str) -> bool:
    lower = text.lower()
    return not any(bad in lower for bad in HARD_BLOCK.union(SOFT_BLOCK, SPAM_BLOCK))

def clean_message(text: str) -> str:
    # remove @mentions and links
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # if emote is repeated more than 3 times
    tokens = text.split()
    cleaned, last, streak = [], None, 0
    for token in tokens:
        if token == last:
            streak += 1
            if streak <= 3:
                cleaned.append(token)
        else:
            streak = 1
            cleaned.append(token)
            last = token
    return " ".join(cleaned).strip()

# logging
def log_event(file, content):
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {content}\n")

# bot class
class LilVikBot(Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix="!",
            initial_channels=[CHANNEL]
        )

        self.message_log = []
        self.model = None
        self.can_speak = True
        self.dynamic_delay = 120  # seconds

        self._load_memory()
        self._initialize_model()
        self.post_counter.start()

    def _load_memory(self):
        if os.path.exists("learned.log"):
            with open("learned.log", "r", encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (.+)", line)
                    if match:
                        self.message_log.append(match.group(1).strip())
            if len(self.message_log) > MAX_MEMORY:
                self.message_log = self.message_log[-MAX_MEMORY:]
            print(f"[LOAD] Loaded {len(self.message_log)} messages from learned.log")

    def _initialize_model(self):
        if self.message_log:
            self.model = markovify.NewlineText("\n".join(self.message_log))
            print("[MODEL] Initialized from loaded memory")

    async def event_ready(self):
        print(f"[READY] Connected as {self.nick}")
        await asyncio.sleep(5)

    async def event_join(self, channel, user):
        if user.name == self.nick:
            print(f"[JOINED] {self.nick} has joined #{channel.name}")

    async def event_message(self, message):
        if message.echo:
            return

        cleaned = clean_message(message.content.strip())
        print(f"[MESSAGE] Received: {message.content.strip()} -> Cleaned: {cleaned}")

        if 3 < len(cleaned) < 200 and is_learnable(cleaned):
            print("[LEARN] Passed filter")
            if cleaned not in self.message_log:
                self.message_log.append(cleaned)
                log_event("learned.log", cleaned)
                print("[LEARN] Appended and logged")
                if len(self.message_log) > MAX_MEMORY:
                    self.message_log.pop(0)
                if len(self.message_log) % 50 == 0:
                    print("[TRAINING] Updating Markov model...")
                    self.model = markovify.NewlineText("\n".join(self.message_log))
        else:
            print("[SKIP] Message not learnable or too short/long")

    @routine(seconds=30.0)
    async def post_counter(self):
        if not BOT_ACTIVE or not self.can_speak:
            return
        channel = self.connected_channels[0] if self.connected_channels else None
        if not channel:
            print("[WARN] Channel not joined yet.")
            return

        await asyncio.sleep(self.dynamic_delay)
        self.dynamic_delay = random.randint(120, 300)  #2–5 minutes

        message = None
        if self.model:
            for _ in range(5):
                candidate = self.model.make_short_sentence(200)
                print(f"[MODEL TRY] {candidate}")
                if candidate and is_speakable(candidate):
                    message = candidate
                    break

        if not message:
            message = random.choice(["just vibing", "KEKW", "peepoHappy", "<3"])

        try:
            await channel.send(message)
            log_event("spoken.log", message)
            print(f"[SENT] {message} (next in {self.dynamic_delay}s)")
        except Exception as e:
            print(f"[FAIL] {e}")
            self.can_speak = False

if __name__ == "__main__":
    bot = LilVikBot()
    bot.run()
