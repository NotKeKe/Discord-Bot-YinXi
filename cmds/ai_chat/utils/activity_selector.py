import discord
from typing import Optional
import random
import orjson
from httpx import AsyncClient
import aiosqlite
import logging

from cmds.ai_chat.chat.chat import Chat
from core.mongodb import MongoDB_DB
from core.functions import current_time, async_translate, halfToFull

path = './data/lovelive.db'
logger = logging.getLogger(__name__)

class ActivitySelector:
    past_status = []

    _inited = False

    @classmethod
    async def init(cls):
        if cls._inited:
            return
        
        async with aiosqlite.connect(path) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        txt TEXT
                    )
                ''')
                await conn.commit()

        cls._inited = True

    @classmethod
    async def activity_select(cls, status: Optional[int] = None) -> Optional[discord.Activity | discord.Game]:
        curr_time = current_time()
        status = random.randint(1, 3) if not status else status

        # base system prompt
        system_prompt = '''
你現在要幫助一個**人**生成一個不重複的他的狀態。
輸出規則:
    - 請輸出**30個字**以內的狀態
    - **請勿使用markdown格式**
    - **請勿使用中文標點符號**
    - 請以他的人物設定作為參照，輸出人性化的狀態訊息。
    - **如果搜尋結果未提供輸出，則自己想一個正常的狀態。**
    - **如果搜尋結果失敗，不要告訴使用者自己沒有搜尋到。**
    - 請使用繁體中文作為輸出。
    - 不要重複使用相同的status
其他:
    - 你今天已經用過的status:
        ```json
        {status}
        ```
'''.format(status = orjson.dumps(cls.past_status[-10:], option=orjson.OPT_INDENT_2).decode()).strip()
        # model = 'ai-local:gemma4-12b'
        model = 'zhipu:glm-4-flash'

        logger.info(f'Status will go to `{status}`, matching...')

        match status:
            # Playing
            case 1:
                async with AsyncClient() as client:
                    resp = await client.get('https://api.lovelive.tools/api/SweetNothings')
                    # get from api
                    if resp.status_code == 200:
                        result = await async_translate(resp.text, 'zh-CN', 'zh-TW')

                        # save to db
                        try:
                            async with aiosqlite.connect(path) as db:
                                async with db.execute("SELECT EXISTS(SELECT 1 FROM data WHERE txt = ?)", (resp.text,)) as cursor:
                                    row = await cursor.fetchone()
                                    exists = bool(row[0]) if row else False

                                if not exists:
                                    await db.execute('INSERT INTO data (txt) VALUES (?)', (resp.text,))
                                    await db.commit()
                        except:
                            logger.error('Error accured at activity_select', exc_info=True)

                    # or generate from model
                    else:
                        client = Chat(model=model, system_prompt=system_prompt)
                        _, result, h = await client.chat(
                            prompt=(
                                f'現在時間為: {curr_time}，'
                                '幫我寫一段emo風格的短文，主題是「孤獨感像海水一樣淹沒我」，' # ??????
                                '要像Instagram (IG)那種中二文青語氣，最好有比喻，'
                                '句子斷裂一點、像心碎在打字。不要使用搜尋功能，你要自己發揮想像力。'
                            ),
                            is_enable_tools=False
                        )

                        # retry to handle model no output
                        for _ in range(3):
                            if result:
                                break

                            _, result, h = await client.chat(
                                prompt='You didn\'t output anything, please OUTPUT your final answer or result after thinking.', 
                                is_enable_tools=False,
                                tool_choice='none',
                                history=h
                            )


                        result = halfToFull(result).replace('。', '\n')
                        cls.past_status.append((f'{curr_time} 正在玩 ' + result))

                    activity = discord.Game(name=result)

            # Listening
            case 2:
                random_num = random.uniform(0, 1) 

                # find song from db (pjsk)
                if random_num >= 0.5: 
                    collection = MongoDB_DB.pjsk['songs']
                    songs = [song.get('songName', '') async for song in collection.find() if 'songName' in song]
                    result = random.choice(songs)
                
                # generate from model (through web_search)
                else:
                    client = Chat(model=model, system_prompt=system_prompt)

                    _, result, h = await client.chat(prompt='基於搜尋，找`一首`有關 `emo` 的歌，確保輸出時僅輸出歌曲的名稱，沒有其他攏言贅字', tool_choice='required')

                    # retry to handle model no output
                    for _ in range(3):
                        if result:
                            break

                        _, result, h = await client.chat(
                            prompt='You didn\'t output anything, please OUTPUT your final answer or result after thinking.', 
                            is_enable_tools=False,
                            tool_choice='none',
                            history=h
                        )

                    result = halfToFull(result).replace('。', '\n')
                    cls.past_status.append((f'{curr_time} 正在聽 ' + result))

                activity = discord.Activity(type=discord.ActivityType.listening, name=result)

            # Watching
            case 3:
                client = Chat(model=model, system_prompt=system_prompt)

                _, result, h = await client.chat(prompt='基於搜尋，找`一部`隨機的`愛情`電影，確保輸出時僅輸出電影的名稱，沒有其他攏言贅字', tool_choice='required')
                
                # retry to handle model no output
                for _ in range(3):
                    if result:
                        break

                    _, result, h = await client.chat(
                        prompt='You didn\'t output anything, please OUTPUT your final answer or result after thinking.', 
                        is_enable_tools=False,
                        tool_choice='none',
                        history=h
                    )


                result = halfToFull(result).replace('。', '\n')
                cls.past_status.append((f'{curr_time} 正在聽 ' + result))

                activity = discord.Activity(type=discord.ActivityType.watching, name=result)
            
            case _:
                return

        return activity