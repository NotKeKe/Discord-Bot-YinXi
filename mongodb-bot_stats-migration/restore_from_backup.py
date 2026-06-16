'''
一次性修復腳本：從 backup_original.json 還原 DB，並把 Unknown 桶裡
已識別的 keep/show_keep/del_keep 合併進 Keep cog。

這個腳本只跑一次，僅在 2026-06-16 第二次 migrate_stats.py 損毀 DB 後使用。
'''

import json
import os
from urllib.parse import quote_plus

import pymongo
from bson import json_util
from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

BACKUP_PATH = os.path.join(os.path.dirname(__file__), 'backup_original.json')
SETTING_JSON_PATH = os.path.join(BASE_DIR, 'setting.json')
DB_NAME = 'bot_collect_stats'
COLLECTION_NAME = 'stats'

RESOLVED_FROM_UNKNOWN = {'keep', 'show_keep', 'del_keep'}
TARGET_COG = 'Keep'


def main() -> int:
    with open(SETTING_JSON_PATH, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    device_ip = settings.get('DEVICE_IP') or '127.0.0.1'
    port = os.getenv('MONGO_PORT', '27020')
    user = quote_plus(os.getenv('MONGO_USER', ''))
    password = quote_plus(os.getenv('MONGO_PASSWORD', ''))
    url = f'mongodb://{user}:{password}@{device_ip}:{port}/'

    with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
        raw = f.read()
    docs = json_util.loads(raw)
    print(f'[INFO] 從 {BACKUP_PATH} 讀取 {len(docs)} 筆文件')

    moved_total = 0
    for doc in docs:
        if doc.get('type') != 'on_command' or doc.get('name') != 'Command called times':
            continue
        data = doc.get('data') or {}
        unknown = data.get('Unknown') or {}
        if not unknown:
            continue

        keep_bucket = data.setdefault(TARGET_COG, {})
        for cmd, count in unknown.items():
            if cmd in RESOLVED_FROM_UNKNOWN:
                existing = keep_bucket.get(cmd, 0)
                keep_bucket[cmd] = existing + count
                moved_total += count
                print(f'  [MOVE] data.Unknown.{cmd} ({count}) -> data.{TARGET_COG}.{cmd}')

        del data['Unknown']
        print(f'  [OK] 移除已空的 Unknown 桶')

    print(f'\n[INFO] 共搬移 {moved_total} 次呼叫進 {TARGET_COG} cog')

    client = pymongo.MongoClient(url)
    client.admin.command('ping')
    collection = client[DB_NAME][COLLECTION_NAME]

    collection.delete_many({})
    print('[INFO] 已清空現有 collection')

    inserted = collection.insert_many(docs)
    print(f'[INFO] 已寫入 {len(inserted.inserted_ids)} 筆文件')

    print('\n=== 還原後 DB 狀態 ===')
    for d in collection.find({}, sort=[('type', pymongo.ASCENDING), ('name', pymongo.ASCENDING)]):
        name = d.get('name', '?')
        type_ = d.get('type', '?')
        total = d.get('total_times', '-')
        cogs = list((d.get('data') or {}).keys())
        print(f'  type={type_!r:55s} name={name!r:40s} total={total} cogs={cogs}')

    client.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
