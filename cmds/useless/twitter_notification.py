raise ImportError('twitter_notification not ready yet')

import discord
from discord.ext import commands
import tweepy
import logging
import traceback

# 設置 logging 模塊
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('error.log', 'a', 'utf-8')])

# Twitter API 設置
TWITTER_API_KEY = 'YOUR_TWITTER_API_KEY'
TWITTER_API_SECRET_KEY = 'YOUR_TWITTER_API_SECRET_KEY'
TWITTER_ACCESS_TOKEN = 'YOUR_TWITTER_ACCESS_TOKEN'
TWITTER_ACCESS_TOKEN_SECRET = 'YOUR_TWITTER_ACCESS_TOKEN_SECRET'

auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET_KEY)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
twitter_api = tweepy.API(auth)

# Discord Bot 設置
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
CHANNEL_ID = YOUR_DISCORD_CHANNEL_ID  # 替換為您的 Discord 頻道 ID

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Twitter Stream Listener
class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        try:
            if status.user.screen_name == 'TARGET_TWITTER_USERNAME':  # 替換為目標 Twitter 用戶名
                message = f"New tweet from {status.user.screen_name}: {status.text}"
                channel = bot.get_channel(CHANNEL_ID)
                bot.loop.create_task(channel.send(message))
        except Exception as e:
            logging.error(f"An error occurred: {e}\n{traceback.format_exc()}")

    def on_error(self, status_code):
        if status_code == 420:
            return False  # Disconnects the stream

# 啟動 Twitter Stream
stream_listener = MyStreamListener()
stream = tweepy.Stream(auth=twitter_api.auth, listener=stream_listener)
stream.filter(follow=['TARGET_TWITTER_USER_ID'], is_async=True)  # 替換為目標 Twitter 用戶 ID

# 啟動 Discord Bot
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(DISCORD_TOKEN)
