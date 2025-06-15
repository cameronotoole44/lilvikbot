# AI chatter - lilvikbot

a lightweight chatbot that learns from live chat using Markov chains. it mimics the style and tone of stream conversations and can follow streamers through raids, keeping the conversation going across different communities. it also posts occasional thoughts to [Bluesky](https://bsky.app/profile/lilvikbot.bsky.social), based on what it’s seen.

## features

- connects to Twitch chat via IRC (using `twitchio`)
- passively listens and logs chat messages
- builds a local Markov model to mimic the flow of real-time Twitch conversations
- occasionally sends messages into chat based on what it’s learned
- posts once or twice daily to Bluesky
- includes TOS-safe filtering and cooldown logic to avoid spam or sketchy output
- manual kill switch, logging, and moderation auditing built in
- designed to be lightweight, quiet, and autonomous

## how it works

1. the bot connects to a specified Twitch channel.
2. it listens to live chat and logs meaningful messages.
3. every 50 messages, it retrains its Markov model.
4. at randomized intervals, it generates a message and speaks in chat (if allowed).
5. once or twice a day, it posts a bluesky post based on learned phrases.
6. it can be manually moved from one chat to another, like when a streamer raids or hosts a new channel.

## moderation

- `hard_block.txt`: words that should never be learned or repeated.
- `soft_block.txt`: words it can learn, but will never speak.
- `spam_block.txt`: filters for low-effort or repetitive content.

note: `hard_block.txt` is not included in this repo to avoid hosting offensive language. for a comprehensive open-source list of banned words, check out [LDNOOBW's banned word list](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words).

## roadmap

**implemented**

- (っ ▀¯▀)つ twitch chat logging + markov model generation
- (っ ▀¯▀)つ passive chat mimicry
- (っ ▀¯▀)つ safe message filtering
- (っ ▀¯▀)つ bluesky auto-posting

**in progress**

- ( ˇ෴ˇ ) auto-follow twitch raids
- ( ˇ෴ˇ ) persistent memory across sessions
- ( ˇ෴ˇ ) tone/personality tuning via seed messages
- ( ˇ෴ˇ ) twitter auto-posting

not your typical chatbot. just vibes.
