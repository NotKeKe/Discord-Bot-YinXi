from core.functions import mongo_db_client

class MongoDB_DB:
    aichannel_chat_history = mongo_db_client['aichannel_chat_history']
    aichat_available_models = mongo_db_client['aichat_available_models']
    aichat_chat_history = mongo_db_client['aichat_chat_history']
    bot_collect_stats = mongo_db_client['bot_collect_stats']
    keep = mongo_db_client['keep']
    sub_yt = mongo_db_client['sub_yt']
    pjsk = mongo_db_client['pjsk']