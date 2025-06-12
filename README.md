

# AI chatter - lilvikbot

a lightweight, Twitch native chatbot that learns from live chat using Markov chains. it mimics the style and tone of stream conversations and can follow streamers through raids to keep the conversation flowing in new channels. making it throughout different communities on Twitch

## features

- connects to Twitch chat via IRC (using `twitchio`)
- builds a local Markov model based on recent messages
- TOS-safe filtering + cooldown to prevent spamming
- designed to be lightweight and customizable

## how it works

1. The bot connects to a specified Twitch channel.
2. It listens to chat and logs meaningful messages.
3. Every 50 messages, it retrains its Markov model.

