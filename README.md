# AI chatter - lilvikbot

a lightweight, Twitch native chatbot that learns from live chat using Markov chains. it mimics the style and tone of stream conversations and can follow streamers through raids to keep the conversation flowing in new channels making its way through different communities on Twitch. it also posts occasional thoughts to Twitter, based on what it’s seen.

## features

- connects to Twitch chat via IRC (using `twitchio`)
- passively listens and logs chat messages
- builds a local Markov model to mimic the style of live Twitch conversations
- posts once or twice daily to Twitter using learned phrases
- occasionally sends messages into chat, based on what it's learned
- includes TOS-safe filtering and cooldown logic to avoid spam
- designed to be lightweight, quiet, and autonomous

## how it works

1. the bot connects to a specified Twitch channel.
2. it listens to live chat and logs meaningful messages.
3. every 50 messages, it retrains its Markov model.
4. on a timed interval (not triggered by commands), it generates a sentence and sends it to Twitch chat.
5. once or twice a day, it tweets a generated message based on its Twitch memory.
6. it can be manually moved from one chat to another, such as when a streamer raids a new channel.

## roadmap

- twitch chat logging + markov model generation
- passive chat mimicry
- twitter auto-posting
- auto-follow twitch raids
- kick.com support
- persistent memory across sessions
- tone/personality tuning via seed messages

not your typical chatbot. just vibes.
