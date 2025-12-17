import hashlib

# token -> (audio_url, guild_id)
tokens = {}

def get_token(audio_url: str, guild_id: str) -> str:
    # 用 audio_url + guild_id 算 hash
    text = audio_url + guild_id
    token = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if token not in tokens:
        tokens[token] = (audio_url, guild_id)
    return token

def get_audio_url(token: str, guild_id: str) -> str | None:
    # 驗證 token 是否存在且 guild_id 相符
    if token in tokens and tokens[token][1] == guild_id:
        return tokens[token][0]

def delete_token(token: str):
    if token in tokens:
        del tokens[token]