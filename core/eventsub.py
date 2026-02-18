import os
import json
import asyncio
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "").strip()
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
EVENTSUB_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix"

logger = logging.getLogger(__name__)


class RaidFollower:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.session_id = None
        self.app_access_token = None
        self.ws = None
        self.running = False
        self.broadcaster_id = None
        self.subscribed_channels = set()
    
    async def get_access_token(self):
        token = os.getenv("TWITCH_OAUTH_TOKEN", "").strip().replace("oauth:", "")
        if token:
            self.app_access_token = token
            logger.info("[EVENTSUB] Using bot OAuth token")
            return True
        else:
            logger.error("[EVENTSUB ERROR] No OAuth token found")
            return False
    
    async def get_broadcaster_id(self, channel_name: str) -> str | None:
        url = f"{TWITCH_API_URL}/users"
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {self.app_access_token}"
        }
        params = {"login": channel_name.lower()}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                logger.info(f"[EVENTSUB DEBUG] Looking up user '{channel_name}': status {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"[EVENTSUB DEBUG] Response: {data}")
                    if data["data"]:
                        broadcaster_id = data["data"][0]["id"]
                        logger.info(f"[EVENTSUB] Found broadcaster ID for {channel_name}: {broadcaster_id}")
                        return broadcaster_id
                else:
                    error = await resp.text()
                    logger.error(f"[EVENTSUB ERROR] User lookup failed: {error}")
        return None
    
    async def subscribe_to_raids(self, broadcaster_id: str, channel_name: str = "unknown"):
        if broadcaster_id in self.subscribed_channels:
            logger.info(f"[EVENTSUB] Already subscribed to raids from {channel_name} ({broadcaster_id})")
            return True
        
        url = f"{TWITCH_API_URL}/eventsub/subscriptions"
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {self.app_access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "type": "channel.raid",
            "version": "1",
            "condition": {
                "from_broadcaster_user_id": broadcaster_id
            },
            "transport": {
                "method": "websocket",
                "session_id": self.session_id
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 202:
                    self.subscribed_channels.add(broadcaster_id)
                    logger.info(f"[EVENTSUB] Subscribed to raids from {channel_name} ({broadcaster_id})")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"[EVENTSUB ERROR] Failed to subscribe to {channel_name}: {resp.status} - {error}")
                    return False
    
    async def handle_message(self, message: dict):
        """Handle incoming EventSub messages."""
        msg_type = message.get("metadata", {}).get("message_type")
        
        if msg_type == "session_welcome":
            self.session_id = message["payload"]["session"]["id"]
            logger.info(f"[EVENTSUB] Connected, session_id: {self.session_id}")
            
            channel = os.getenv("TWITCH_CHANNEL", "").strip()
            self.broadcaster_id = await self.get_broadcaster_id(channel)
            if self.broadcaster_id:
                await self.subscribe_to_raids(self.broadcaster_id, channel)
            else:
                logger.error(f"[EVENTSUB ERROR] Could not find broadcaster ID for {channel}")
        
        elif msg_type == "session_keepalive":
            pass  
        
        elif msg_type == "notification":
            await self.handle_notification(message["payload"])
        
        elif msg_type == "session_reconnect":
            reconnect_url = message["payload"]["session"]["reconnect_url"]
            logger.info(f"[EVENTSUB] Reconnecting to {reconnect_url}")
            await self.reconnect(reconnect_url)
        
        elif msg_type == "revocation":
            logger.warning(f"[EVENTSUB] Subscription revoked: {message['payload']}")
    
    async def handle_notification(self, payload: dict):
        """Handle event notifications."""
        event_type = payload.get("subscription", {}).get("type")
        event_data = payload.get("event", {})
        
        if event_type == "channel.raid":
            from_channel = event_data.get("from_broadcaster_user_name")
            to_channel = event_data.get("to_broadcaster_user_name")
            viewers = event_data.get("viewers")
            
            logger.info(f"[RAID EVENT] {from_channel} raided {to_channel} with {viewers} viewers")
            
            await self.follow_raid(to_channel, viewers)
    
    async def follow_raid(self, channel_name: str, viewers: int):
        channel_lower = channel_name.lower()
        
        logger.info(f"[RAID] Attempting to follow raid to #{channel_lower}")
        
        if channel_lower not in self.bot.raided_channels:
            try:
                await self.bot.join_channels([channel_lower])
                self.bot.raided_channels.add(channel_lower)
                
                # log it
                from bot import log_event, RAID_LOG_FILE
                log_event(RAID_LOG_FILE, f"{channel_lower} ({viewers} viewers)")
                
                logger.info(f"[RAID] Successfully joined #{channel_lower}")
                
                # subscribe to raids from the new channel too (chain following)
                logger.info(f"[RAID CHAIN] Setting up raid subscription for #{channel_lower}")
                new_broadcaster_id = await self.get_broadcaster_id(channel_lower)
                if new_broadcaster_id:
                    success = await self.subscribe_to_raids(new_broadcaster_id, channel_lower)
                    if success:
                        logger.info(f"[RAID CHAIN] Now following raids from #{channel_lower}")
                    else:
                        logger.error(f"[RAID CHAIN ERROR] Failed to subscribe to raids from #{channel_lower}")
                else:
                    logger.error(f"[RAID CHAIN ERROR] Could not get broadcaster ID for #{channel_lower}")
                
            except Exception as e:
                logger.error(f"[RAID ERROR] Failed to join #{channel_lower}: {e}")
        else:
            logger.info(f"[RAID] Already tracking #{channel_lower}")
    
    async def reconnect(self, url: str):
        if self.ws:
            await self.ws.close()
        self.subscribed_channels.clear()
        await self.connect(url)
    
    async def connect(self, url: str = EVENTSUB_WS_URL):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                self.ws = ws
                logger.info(f"[EVENTSUB] WebSocket connected to {url}")
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        await self.handle_message(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"[EVENTSUB ERROR] WebSocket error: {ws.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.info(f"[EVENTSUB] WebSocket closed")
                        break
    
    async def start(self):
        self.running = True
        
        if not await self.get_access_token():
            logger.error("[EVENTSUB ERROR] Cannot start without access token")
            return
        
        while self.running:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"[EVENTSUB ERROR] Connection failed: {e}")
            
            if self.running:
                logger.info("[EVENTSUB] Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
    
    def stop(self):
        self.running = False
        if self.ws:
            asyncio.create_task(self.ws.close())

async def run_with_bot(bot_instance):
    raid_follower = RaidFollower(bot_instance)
    await raid_follower.start()
