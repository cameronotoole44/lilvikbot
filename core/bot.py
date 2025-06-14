import os
import re
import random
import asyncio
import markovify
from twitchio.ext.commands import Bot
from twitchio.ext.routines import routine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TWITCH_OAUTH_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "true").lower() == "true"

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

# filter logic
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
    cleaned = []
    last = None
    streak = 0

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
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n")

# bot class
class LilVikBot(Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_OAUTH_TOKEN,
            prefix="!",
            initial_channels=[TWITCH_CHANNEL]
        )
        self.message_log = []
        self.model = None
        self.can_speak = True
        self.dynamic_delay = 120  #seconds
        self.post_counter.start()

    async def event_ready(self):
        print(f"[READY] LilVikBot connected as {self.nick}")
        await asyncio.sleep(5)

    async def event_join(self, channel, user):
        if user.name == self.nick:
            print(f"[JOINED] LilVikBot has joined #{channel.name}")

    async def event_message(self, message):
        if message.echo:
            return

        raw = message.content.strip()
        cleaned = clean_message(raw)

        if 3 < len(cleaned) < 200 and is_learnable(cleaned):
            if cleaned not in self.message_log:
                self.message_log.append(cleaned)
                log_event("learned.log", cleaned)

            if len(self.message_log) % 50 == 0:
                print("[TRAINING] Updating Markov model...")
                text = "\n".join(self.message_log)
                self.model = markovify.NewlineText(text)

    @routine(seconds=30.0)
    async def post_counter(self):
        if not BOT_ACTIVE or not self.can_speak:
            return

        channel = self.connected_channels[0] if self.connected_channels else None
        if not channel:
            print("[WARN] Channel not yet joined — retrying later.")
            return

        await asyncio.sleep(self.dynamic_delay)
        self.dynamic_delay = random.randint(120, 300)  #2–5 minutes

        message = None
        if self.model:
            for _ in range(5):  # try 5 times to get a safe message
                candidate = self.model.make_short_sentence(200)
                if candidate and is_speakable(candidate):
                    message = candidate
                    break

        if not message:
            message = random.choice([
                "just vibing", "KEKW", "peepoHappy", "<3"
            ])

        try:
            await channel.send(message)
            log_event("spoken.log", message)
            print(f"[SENT] {message} (Next in {self.dynamic_delay}s)")
        except Exception as e:
            print(f"[FAIL] Could not send message: {e}")
            self.can_speak = False

bot = LilVikBot()
bot.run()

