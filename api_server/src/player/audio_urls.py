import hashlib
from collections import OrderedDict

# tokens[token] -> (audio_url, guild_id)
MAX_TOKENS = 2000
tokens = OrderedDict() # 簡易快取

def get_token(audio_url: str, guild_id: str) -> str:
    # 用 audio_url + guild_id 算 hash
    text = audio_url + guild_id
    token = hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    if token in tokens:
        # 最近使用
        tokens.move_to_end(token)
    else:
        tokens[token] = (audio_url, guild_id)
        # delete oldest
        if len(tokens) > MAX_TOKENS:
            tokens.popitem(last=False)
            
    return token

def get_audio_url(token: str, guild_id: str) -> str | None:
    if token in tokens and tokens[token][1] == guild_id:
        # 移至最後 最近使用
        tokens.move_to_end(token)
        return tokens[token][0]