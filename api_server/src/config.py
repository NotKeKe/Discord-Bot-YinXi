from dotenv import load_dotenv
import os

load_dotenv()

REDIS = {
    'host': 'redis',
    'port': 6379,
}
'''include host and port'''

DC_BOT_PASSED_KEY = os.getenv('DC_BOT_PASSED_KEY')