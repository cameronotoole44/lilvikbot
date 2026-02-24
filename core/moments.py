import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum

class MomentType(Enum):
    HYPE = "hype"
    SADGE = "sadge"
    EMOTE_SPAM = "emote_spam"
    QUESTION = "question"
    GREETING = "greeting"
    NEUTRAL = "neutral"

@dataclass
class MomentConfig:
    threshold: int
    keywords: set[str]
    fallback_responses: list[str]

MOMENT_CONFIGS: dict[MomentType, MomentConfig] = {
    MomentType.HYPE: MomentConfig(
        threshold=2,
        keywords={
            # classic hype
            'pog', 'poggers', 'pogu', 'pogchamp', 'lets go', 'letsgoo', 'letsgo',
            'gg', 'ez', 'win', 'won', 'clutch', 'insane', 'crazy', 'godlike',
            'sheesh', 'goated', 'dub', 'massive', 'huge',
            # from data - CamelCase
            'pagbounce', 'pagchomp', 'pagman', 'verypog', 'pausershype', 'twitchconhype',
            'feelsstrongman', 'feelsamazingman', 'imhim', 'bouncinonit', 'robloxcheer',
            'griddygoose', 'fallwinning',
            # from data - ALL CAPS
            'sick', 'wicked', 'holy', 'king', 'letsgo', 'lets',
            'noway', 'aintnoway', 'noted',
        },
        fallback_responses=['LETSGO', 'SICK', 'PogChamp', 'KING', 'WICKED', 'PagBounce']
    ),
    MomentType.SADGE: MomentConfig(
        threshold=2,
        keywords={
            # classic sad
            'rip', 'sadge', 'sadchamp', 'died', 'dead', 'unlucky', 'pain',
            'pepehands', 'widepeeposad', 'lost', 'lose', 'choke', 'threw', 'ff',
            # from data - CamelCase
            'reefersad', 'bigsad', 'porosad', 'notlikethis', 'reallymad', 'ultramad',
            'wutface', 'donowall', 'pleasestreamer', 'needheal',
            # from data - ALL CAPS
            'icant', 'noooo', 'noooyoucant', 'ewww',
        },
        fallback_responses=['Sadge', 'pain', 'NotLikeThis', 'ICANT', 'ReeferSad', 'BigSad']
    ),
    MomentType.GREETING: MomentConfig(
        threshold=2,
        keywords={
            'hi', 'hello', 'hey', 'sup', 'yo', 'hii', 'hewwo', 'heyy',
            'whats up', 'wassup', 'waddup', 'greetings',
            # from data
            'suphomie', 'heyguys', 'raiders',
        },
        fallback_responses=['hey chat', 'yo', 'SupHomie', 'HeyGuys']
    ),
    MomentType.QUESTION: MomentConfig(
        threshold=3,
        keywords=set(),
        fallback_responses=['good question', 'true', 'hmm']
    ),
    MomentType.EMOTE_SPAM: MomentConfig(
        threshold=4,
        keywords=set(),
        fallback_responses=['KEKW', 'LUL', 'PepeLaugh', 'DinkDonk', 'BaNGER', 'LULW']
    ),
}

COMMON_EMOTES = {
    # classic bttv/ffz/7tv
    'kekw', 'lulw', 'lul', 'lule', 'omegalul', 'pepega', 'monkas', 'pogchamp', 'pogu',
    'poggers', 'pepelaugh', 'catjam', 'peepo', 'peepohappy', 'widepeeposad',
    'sadge', 'copium', 'hopium', 'clueless', 'aware', 'gigachad', 'based',
    'modcheck', 'pausechamp', 'pepejam', 'peped', 'feelsstrongman', 'feelsbadman',
    'feelsgoodman', 'trihard', 'kreygasm', 'residentsleeper', 'notlikethis',
    'biblethump', 'dansgame', 'wutface', 'jebaited', 'hypers', 'pogo', '4head',
    # from data - high frequency CamelCase
    'pauseman', 'banger', 'dinkdonk', 'ravetime', 'wideravetime', 'suphomie',
    'reefersad', 'pagbounce', 'widehardo', 'weirddude', 'pausershype', 'pagchomp',
    'imhim', 'cokeshakey', 'speedlaugh', 'puzzletime', 'ashtwerk', 'socute',
    'ofcourse', 'kappaross', 'giannislaugh', 'feelsdankman', 'dinodance',
    'robloxcheer', 'singsmic', 'seemsgood', 'thevoices', 'verypog', 'soyr',
    'pepepls', 'jamfrog', 'bigsad', 'tylerlaugh', 'permavibing', 'pausemansit',
    'pagman', 'feelsrainman', 'lebron', 'feelsamazingman', 'vislaud', 'pepog',
    'pewpewpew', 'heyguys', 'griddygoose', 'donowall', 'awkwardsmile', 'aliendance',
    'bouncinonit', 'cannonboltpls', 'quarterjade', 'reallymad', 'reallynow',
    # from data - ALL CAPS
    'lol', 'lmao', 'omg', 'oooo', 'aaaa', 'monka', 'nodders',
    'saj', 'muga', 'jarvis', 'frog', 'mytrueform', 'schizo', 'wajaja',
    'icant', 'noooyoucant', 'aintnoway', 'noway', 'vibe', 'gulp', 'crab',
    'omegadancebutfast', 'kooby',
}


class MomentDetector:
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.context_window: list[str] = []
    
    def add_message(self, message: str):
        self.context_window.append(message.lower())
        if len(self.context_window) > self.window_size:
            self.context_window.pop(0)
    
    def clear(self):
        self.context_window.clear()
    
    def detect(self) -> MomentType:
        if len(self.context_window) < 3:
            return MomentType.NEUTRAL
        
        recent = self.context_window[-10:]
        combined = ' '.join(recent)
        
        emote_count = self._count_emote_messages(recent)
        if emote_count >= MOMENT_CONFIGS[MomentType.EMOTE_SPAM].threshold:
            return MomentType.EMOTE_SPAM
        
        question_count = sum(1 for msg in recent if '?' in msg)
        if question_count >= MOMENT_CONFIGS[MomentType.QUESTION].threshold:
            return MomentType.QUESTION
        
        for moment_type in [MomentType.HYPE, MomentType.SADGE, MomentType.GREETING]:
            config = MOMENT_CONFIGS[moment_type]
            hit_count = sum(1 for msg in recent if self._contains_keyword(msg, config.keywords))
            if hit_count >= config.threshold:
                return moment_type
        
        return MomentType.NEUTRAL
    
    def _count_emote_messages(self, messages: list[str]) -> int:
        count = 0
        for msg in messages:
            tokens = msg.split()
            if not tokens:
                continue
            emote_tokens = sum(1 for t in tokens if t.lower() in COMMON_EMOTES or self._looks_like_emote(t))
            if emote_tokens >= len(tokens) * 0.5:
                count += 1
        return count
    
    def _looks_like_emote(self, token: str) -> bool:
        if len(token) < 2:
            return False
        if token.isupper() and len(token) >= 3:
            return True
        if re.match(r'^[A-Z][a-z]+[A-Z]', token):
            return True
        # common 7TV prefixes
        lower = token.lower()
        if lower.startswith(('pepe', 'peepo', 'feels', 'wide', 'cat', 'pog', 'pause')):
            return True
        # common 7TV suffixes
        if lower.endswith(('ge', 'gers', 'jam', 'time', 'dance', 'hype', 'man', 'sad')):
            return True
        return False
    
    def _contains_keyword(self, message: str, keywords: set[str]) -> bool:
        tokens = set(re.findall(r'\b\w+\b', message.lower()))
        if tokens & keywords:
            return True
        for kw in keywords:
            if ' ' in kw and kw in message:
                return True
        return False
    
    def get_fallback(self, moment: MomentType) -> str:
        import random
        config = MOMENT_CONFIGS.get(moment)
        if config and config.fallback_responses:
            return random.choice(config.fallback_responses)
        return random.choice(['true', 'KEKW', 'PepeLaugh', '<3'])
    
    def get_moment_keywords(self, moment: MomentType) -> set[str]:
        config = MOMENT_CONFIGS.get(moment)
        if config:
            return config.keywords
        return set()
