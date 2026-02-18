import os
import re
import random
import asyncio
import logging
import markovify
from twitchio.ext.commands import Bot
from twitchio.ext.routines import routine
from dotenv import load_dotenv
from datetime import datetime

from moments import MomentDetector, MomentType, MOMENT_CONFIGS

load_dotenv()

raw_token = os.getenv("TWITCH_OAUTH_TOKEN", "").strip()
TOKEN = raw_token.replace("oauth:", "")
CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip()
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "true").lower() == "true"
FOLLOW_RAIDS = os.getenv("FOLLOW_RAIDS", "true").lower() == "true"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
FILTER_DIR = os.path.join(BASE_DIR, "..", "filters")

LOG_FILE = os.path.join(DATA_DIR, "bot_debug.log")
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MAX_MEMORY = 10000
LEARNED_LOG = os.path.join(DATA_DIR, "learned.log")
SPOKEN_LOG = os.path.join(DATA_DIR, "spoken.log")
RAID_LOG_FILE = os.path.join(DATA_DIR, "raided_channels.log")


def load_forbidden_words(filename):
    path = os.path.join(FILTER_DIR, filename)
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
logger.info(f"[FILTER] Loaded {len(HARD_BLOCK)} hard, {len(SOFT_BLOCK)} soft, {len(SPAM_BLOCK)} spam blocks")


def is_learnable(text: str) -> bool:
    lower = text.lower()
    return not any(bad in lower for bad in HARD_BLOCK)


def is_speakable(text: str) -> bool:
    lower = text.lower()
    return not any(bad in lower for bad in HARD_BLOCK.union(SOFT_BLOCK, SPAM_BLOCK))


def clean_message(text: str) -> str:
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

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


def log_event(file, content):
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {content}\n")


def load_joined_channels():
    if not os.path.exists(RAID_LOG_FILE):
        return set()
    with open(RAID_LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip().split("] ")[-1].split(" (")[0].lower() for line in f if "] " in line)


class LilVikBot(Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix="!", initial_channels=[CHANNEL])

        self.message_log = []
        self.model = None
        self.can_speak = True
        self.dynamic_delay = 120
        self.raided_channels = load_joined_channels()
        self.moment_detector = MomentDetector(window_size=15)
        self.raid_follower = None
        self.post_counter.start()

        self._load_memory()
        self._initialize_model()

    def _load_memory(self):
        if os.path.exists(LEARNED_LOG):
            with open(LEARNED_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (.+)", line)
                    if match:
                        self.message_log.append(match.group(1).strip())
            if len(self.message_log) > MAX_MEMORY:
                self.message_log = self.message_log[-MAX_MEMORY:]
            logger.info(f"[LOAD] Loaded {len(self.message_log)} messages from learned.log")

    def _initialize_model(self):
        if self.message_log:
            self.model = markovify.NewlineText("\n".join(self.message_log))
            logger.info("[MODEL] Initialized from loaded memory")

    async def event_ready(self):
        logger.info(f"[READY] Connected as {self.nick}")
        
        if FOLLOW_RAIDS:
            from eventsub import RaidFollower
            self.raid_follower = RaidFollower(self)
            asyncio.create_task(self.raid_follower.start())
            logger.info("[READY] EventSub raid follower started")
        
        await asyncio.sleep(5)

    async def event_join(self, channel, user):
        if user.name == self.nick:
            logger.info(f"[JOINED] {self.nick} has joined #{channel.name}")

    async def event_message(self, message):
        if message.echo:
            return

        cleaned = clean_message(message.content.strip())
        logger.info(f"[MESSAGE] {cleaned}")

        self.moment_detector.add_message(cleaned)
        
        logger.info(f"[MOMENT DEBUG] {self.moment_detector.detect().value}")

        if 3 < len(cleaned) < 200 and is_learnable(cleaned):
            if cleaned not in self.message_log:
                self.message_log.append(cleaned)
                log_event(LEARNED_LOG, cleaned)
                if len(self.message_log) > MAX_MEMORY:
                    self.message_log.pop(0)
                if len(self.message_log) % 50 == 0:
                    logger.info("[TRAINING] Updating Markov model...")
                    self.model = markovify.NewlineText("\n".join(self.message_log))

    def generate_contextual_message(self) -> str | None:
        moment = self.moment_detector.detect()
        logger.info(f"[MOMENT] Detected: {moment.value}")

        if not self.model:
            return self.moment_detector.get_fallback(moment)

        if moment == MomentType.EMOTE_SPAM:
            return self.moment_detector.get_fallback(moment)

        if moment != MomentType.NEUTRAL:
            keywords = self.moment_detector.get_moment_keywords(moment)
            candidate = self._generate_with_keywords(keywords)
            if candidate:
                return candidate
            return self.moment_detector.get_fallback(moment)

        for _ in range(5):
            candidate = self.model.make_short_sentence(200)
            if candidate and is_speakable(candidate):
                return candidate

        return self.moment_detector.get_fallback(MomentType.NEUTRAL)

    def _generate_with_keywords(self, keywords: set[str]) -> str | None:
        for _ in range(10):
            candidate = self.model.make_short_sentence(200)
            if not candidate or not is_speakable(candidate):
                continue
            lower = candidate.lower()
            if any(kw in lower for kw in keywords):
                return candidate
        return None

    @routine(seconds=30.0)
    async def post_counter(self):
        if not BOT_ACTIVE or not self.can_speak:
            return
        channel = self.connected_channels[0] if self.connected_channels else None
        if not channel:
            logger.warning("[WARN] Channel not joined yet.")
            return

        await asyncio.sleep(self.dynamic_delay)
        self.dynamic_delay = random.randint(120, 300)

        message = self.generate_contextual_message()

        if not message:
            message = random.choice(["just vibing", "KEKW", "peepoHappy", "<3"])

        try:
            await channel.send(message)
            log_event(SPOKEN_LOG, f"[{self.moment_detector.detect().value}] {message}")
            logger.info(f"[SENT] {message} (moment: {self.moment_detector.detect().value}, next in {self.dynamic_delay}s)")
        except Exception as e:
            logger.error(f"[FAIL] {e}")
            self.can_speak = False


if __name__ == "__main__":
    bot = LilVikBot()
    bot.run()
