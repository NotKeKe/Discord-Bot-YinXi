'''
MongoDB 統計資料遷移腳本
=========================

將 `bot_collect_stats.stats` 從舊格式遷移至用戶指定的新格式。

流程：
  Step 1: 連接 MongoDB，將現有資料全部備份至 `migration/backup_original.json`
  Step 2: 刪除 `bot_collect_stats` 資料庫
  Step 3: 依新格式重組資料並寫回
  Step 4: 驗證寫入結果

使用方式：
  uv run migration/migrate_stats.py
  或： uvx --from pymongo --from motor python migration/migrate_stats.py

注意：
  - 執行前請確認 Discord Bot 已離線
  - 腳本本身「不會」刪除 `backup_original.json`，此檔案為安全網
  - 重複執行（DB 已為空）會得到相同結果
'''

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import pymongo
from bson import json_util
from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_NAME = 'bot_collect_stats'
COLLECTION_NAME = 'stats'
COGS_JSON_PATH = os.path.join(BASE_DIR, 'cogs.json')
SETTING_JSON_PATH = os.path.join(BASE_DIR, 'setting.json')
BACKUP_PATH = os.path.join(os.path.dirname(__file__), 'backup_original.json')

try:
    with open(SETTING_JSON_PATH, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    DEVICE_IP = settings.get('DEVICE_IP') or '127.0.0.1'
except FileNotFoundError:
    DEVICE_IP = os.getenv('DEVICE_IP', '127.0.0.1')

MONGO_USER = quote_plus(os.getenv('MONGO_USER', ''))
MONGO_PASSWORD = quote_plus(os.getenv('MONGO_PASSWORD', ''))
MONGO_PORT = os.getenv('MONGO_PORT', '27020')
MONGO_URL = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{DEVICE_IP}:{MONGO_PORT}/"


def now_utc8_iso() -> str:
    '''產生 UTC+8 時區的 ISO 格式時間字串'''
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat()


def load_cog_mapping() -> dict[str, str]:
    '''載入 cogs.json 並反轉成 command_name -> cog_name 的對照表'''
    with open(COGS_JSON_PATH, 'r', encoding='utf-8') as f:
        cog_to_cmds: dict[str, list[str]] = json.load(f)

    cmd_to_cog: dict[str, str] = {}
    for cog, cmds in cog_to_cmds.items():
        for cmd in cmds:
            cmd_to_cog[cmd] = cog
    return cmd_to_cog


def backup_database(client: pymongo.MongoClient) -> list[dict]:
    '''備份整個 bot_collect_stats 資料庫至 JSON 檔，回傳備份的文件清單'''
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    documents = list(collection.find({}))

    if os.path.exists(BACKUP_PATH):
        raise RuntimeError(
            f'備份檔 {BACKUP_PATH} 已存在，拒絕覆蓋以避免破壞既有資料。'
            '若要重新備份，請先將舊檔改名或刪除。'
        )

    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2, default=json_util.default)

    print(f'  [OK] 已備份 {len(documents)} 筆文件至 {BACKUP_PATH}')
    return documents


def drop_database(client: pymongo.MongoClient) -> None:
    '''刪除 bot_collect_stats 資料庫'''
    client.drop_database(DB_NAME)
    print(f'  [OK] 已刪除資料庫 {DB_NAME}')


def group_commands_by_cog(
    flat_commands: dict,
    cmd_to_cog: dict[str, str],
) -> dict[str, dict[str, int]]:
    '''將扁平 {command_name: count} 依 cogs.json 分組成巢狀 {cog: {cmd: count}}'''
    grouped: dict[str, dict[str, int]] = {}
    unknown: dict[str, int] = {}

    for cmd_name, count in flat_commands.items():
        cog_name = cmd_to_cog.get(cmd_name)
        if cog_name is None:
            unknown[cmd_name] = count
            continue
        grouped.setdefault(cog_name, {})[cmd_name] = count

    if unknown:
        grouped['Unknown'] = unknown
        print(f'  [INFO] 有 {len(unknown)} 個指令在 cogs.json 中找不到對應 cog，已歸入 Unknown')
    return grouped


def build_on_command(doc: dict, cmd_to_cog: dict[str, str], last_update: str) -> dict:
    '''轉換 on_command 文件'''
    flat_commands = doc.get('commands', {}) or {}
    data = group_commands_by_cog(flat_commands, cmd_to_cog)
    return {
        'type': 'on_command',
        'name': 'Command called times',
        'data': data,
        'total_times': doc.get('total_times', 0),
        'last_update': last_update,
    }


def build_on_command_user_times(doc: dict, last_update: str) -> dict:
    '''轉換 on_command_user_times 文件 (扁平 USER_ID → data)'''
    raw = {k: v for k, v in doc.items() if k not in {'_id', 'type'}}
    return {
        'type': 'on_command',
        'name': 'Command called times by a user',
        'data': raw,
        'last_update': last_update,
    }


def build_on_command_guild_times(doc: dict, last_update: str) -> dict:
    '''轉換 on_command_guild_times 文件 (扁平 GUILD_ID → data)'''
    raw = {k: v for k, v in doc.items() if k not in {'_id', 'type'}}
    return {
        'type': 'on_command',
        'name': 'Command called times by a guild',
        'data': raw,
        'last_update': last_update,
    }


def build_on_ready(doc: dict, last_update: str) -> dict:
    '''轉換 on_ready 文件'''
    return {
        'type': 'on_ready',
        'name': 'Bot ready times',
        'data': {'bot_online_times': doc.get('bot_online_times', 0)},
        'last_update': last_update,
    }


def build_on_command_completion(doc: dict, last_update: str) -> dict:
    '''轉換 on_command_completion 文件 (僅保留 total_times)'''
    return {
        'type': 'on_command_completion, on_app_command_completion',
        'name': 'Completed command times',
        'data': {'total_times': doc.get('total_times', 0)},
        'last_update': last_update,
    }


def build_on_command_error(doc: dict, last_update: str) -> dict:
    '''轉換 on_command_error 文件'''
    return {
        'type': 'on_command_error',
        'name': 'Command error times',
        'data': {
            'commands': doc.get('commands', {}) or {},
            'total_times': doc.get('total_times', 0),
        },
        'last_update': last_update,
    }


def build_top_status(doc: dict, last_update: str) -> dict:
    '''轉換 TOP_STATS → TOP_STATUS 文件'''
    return {
        'type': 'custom',
        'name': 'TOP_STATUS',
        'data': {'start_time': doc.get('start_time')},
        'last_update': last_update,
    }


def build_status_str(last_update: str) -> dict:
    '''新增 status_str 文件 (舊 DB 無此 type)'''
    return {
        'type': 'custom',
        'name': 'Status String',
        'data': {
            'api': 'operational',
            'bot': 'operational',
        },
        'last_update': last_update,
    }


def transform_documents(documents: list[dict], cmd_to_cog: dict[str, str]) -> list[dict]:
    '''依 (type, name) 將舊文件轉換為新格式'''
    last_update = now_utc8_iso()
    new_docs: list[dict] = []
    skipped_types: set[str] = set()

    for doc in documents:
        old_type = doc.get('type')
        old_name = doc.get('name')

        if old_type == 'on_command' and old_name == 'Command called times':
            new_docs.append(build_on_command(doc, cmd_to_cog, last_update))
        elif old_type == 'on_command' and old_name == 'Command called times by a user':
            new_docs.append(build_on_command_user_times(doc, last_update))
        elif old_type == 'on_command' and old_name == 'Command called times by a guild':
            new_docs.append(build_on_command_guild_times(doc, last_update))
        elif old_type == 'on_ready':
            new_docs.append(build_on_ready(doc, last_update))
        elif old_type == 'on_command_completion':
            new_docs.append(build_on_command_completion(doc, last_update))
        elif old_type == 'on_command_error':
            new_docs.append(build_on_command_error(doc, last_update))
        elif old_type == 'TOP_STATS':
            new_docs.append(build_top_status(doc, last_update))
        else:
            skipped_types.add(str((old_type, old_name)))

    new_docs.append(build_status_str(last_update))

    if skipped_types:
        print(f'  [INFO] 已略過未在新格式中的 type/name: {sorted(skipped_types)}')

    return new_docs


def insert_new_documents(client: pymongo.MongoClient, new_docs: list[dict]) -> None:
    '''將新格式文件寫入 bot_collect_stats.stats'''
    collection = client[DB_NAME][COLLECTION_NAME]
    result = collection.insert_many(new_docs)
    print(f'  [OK] 已寫入 {len(result.inserted_ids)} 筆文件')


def verify(client: pymongo.MongoClient) -> None:
    '''驗證寫入結果，逐筆印出新文件摘要'''
    print('\n=== 驗證結果 ===')
    collection = client[DB_NAME][COLLECTION_NAME]
    cursor = collection.find({}, sort=[('type', pymongo.ASCENDING), ('name', pymongo.ASCENDING)])

    for doc in cursor:
        type_ = doc.get('type')
        name = doc.get('name')
        last_update = doc.get('last_update')
        print(f'  - type={type_!r:60s} name={name!r} last_update={last_update}')


def main() -> int:
    print('=== MongoDB 統計資料遷移 ===\n')

    print('[Step 1] 連接 MongoDB 並備份現有資料...')
    client = pymongo.MongoClient(MONGO_URL)
    try:
        client.admin.command('ping')
        print(f'  [OK] 已連線至 {DEVICE_IP}:{MONGO_PORT}')
    except Exception as e:
        print(f'  [ERROR] 無法連線至 MongoDB: {e}')
        return 1

    documents = backup_database(client)

    print('\n[Step 2] 刪除原資料庫...')
    drop_database(client)

    print('\n[Step 3] 載入 cogs.json 並重組資料...')
    cmd_to_cog = load_cog_mapping()
    print(f'  [OK] 已載入 {len(cmd_to_cog)} 個指令對應關係')
    new_docs = transform_documents(documents, cmd_to_cog)
    print(f'  [OK] 已產生 {len(new_docs)} 筆新文件')

    print('\n[Step 4] 寫入新格式文件...')
    insert_new_documents(client, new_docs)

    print('\n[Step 5] 驗證...')
    verify(client)

    client.close()
    print(f'\n=== 遷移完成 ===')
    print(f'備份檔案保留於：{BACKUP_PATH}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
