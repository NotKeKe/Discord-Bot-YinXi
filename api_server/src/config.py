from dotenv import load_dotenv
import os

load_dotenv()

REDIS = {
    'host': 'redis',
    'port': 6379,
}
'''include host and port'''

PLAY_WEBSITE_KEY = os.getenv('PLAY_WEBSITE_KEY')