import hashlib

tokens = {}
urls = {}

def audio_url_to_token(audio_url: str, guild_id: str) -> str:
    token = hashlib.sha256((audio_url + guild_id).encode('utf-8')).hexdigest()[:16]
    tokens[token] = audio_url
    return token

def token_to_audio_url(token: str) -> str:
    return tokens[token]