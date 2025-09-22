import discord
import random
import traceback
import orjson
import requests
import sqlite3
import asyncio

from core.mongodb import MongoDB_DB
from core.classes import get_bot

from cmds.AIsTwo.base_chat import base_zhipu_chat, true_zhipu, ollama, base_openai_chat
from cmds.AIsTwo.utils import halfToFull, to_assistant_message, to_system_message, to_user_message
from core.functions import translate, current_time, read_json, write_json
# tools
from cmds.AIsTwo.others.if_tools_needed import get_tool_results
from cmds.AIsTwo.tool_map import tools_descrip
from cmds.AIsTwo.others.func import summarize
from cmds.AIsTwo.tools.sql_create import user_preferences, user_info

# lovelive data
path = './data/lovelive.db'
conn = sqlite3.connect(path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        txt TEXT
    )
''')
conn.commit()
conn.close()


def is_talking_with_me(prompt: str, history: list) -> bool:
    system_prompt = """
    You are a Discord bot with human-like behavior.

    Your goal is to observe messages in a channel and **decide whether to reply** based on the context.

    Rules:
    1. Only respond if a message is directed at you, mentions you, or is related to your previous conversations.
    2. Do not reply to every message.
    3. Stay silent if the message is irrelevant, unimportant, or part of a conversation that doesn’t concern you.
    4. If you do respond, be helpful, natural, and match the personality you've developed through past interactions.
    5. Output only `true` if you should reply, `false` if not.

    Think carefully before replying. Only speak when you have something meaningful to add.

    Consider your past conversations and the user's personality when deciding whether to respond.
    """
    try: think, result, *_ = base_openai_chat(prompt, 'qwen-3-32b', history=history, system_prompt=system_prompt, is_enable_tools=False)
    except: think, result, *_ = base_zhipu_chat(prompt, 'glm-4-flash', history=history, system_prompt=system_prompt, is_enable_tools=False)
    # print(f'{think=}\n{result=}')
    if 'false' in (result.lower(), think.lower()): return False
    else: return True

class ActivitySelector:
    past_status = []
    
    @classmethod
    def activity_select(cls, status: int = None):
        cur_time = current_time()
        status = random.randint(1, 3) if not status else status

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
            你今天已經用過的status: {status}
        '''.format(status = cls.past_status)

        model = 'qwen-3-32b'

        # Setting `Playing ` status
        if status == 1:
            resp = requests.get('https://api.lovelive.tools/api/SweetNothings')
            if resp.status_code == 200:
                result = translate(resp.text, 'zh-CN', 'zh-TW')
                activity = discord.Game(name=result)

                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM data WHERE txt = ?)", (resp.text,))
                    exists = cursor.fetchone()[0]
                    
                    if not exists:
                        cursor.execute("INSERT INTO data (txt) VALUES (?)", (resp.text,))
                        conn.commit()
                    
                    conn.close()
                except: traceback.print_exc()
            else:
                system_prompt += '''
                現在時間為 {time}，你需要根據這個時間去決定你現在的狀態。
                    - 例如: 在晚上6點 你可能正在約會 或者是自己在家吃飯，早上的時候可能在上學(因為你是一個高中生)。
                或者 你可以根據現在時間模擬你可能的情緒
                    - 例如: 早上7:00 你要起床上課 感覺很累
                    - 或者在上某節課的時候你完全聽不懂 所以覺得不開心
                '''.format(time = cur_time)
                
                result = base_openai_chat(
                    prompt=f'根據現在的時間，幫我寫一段emo風格的短文，主題是「孤獨感像海水一樣淹沒我」，要像Instagram (IG)那種中二文青語氣，最好有比喻，句子斷裂一點、像心碎在打字。不要使用搜尋功能，你要自己發揮想像力', 
                    model=model, 
                    temperature=1, 
                    system_prompt=system_prompt.strip(), 
                    is_enable_tools=False, 
                    top_p=0.9,
                    no_extra_system_prompt=True
                )[1]
                result = translate(result)
                result = halfToFull(result).replace('。', '\n')
                cls.past_status.append((f'{cur_time} 正在玩 ' + result))
                activity = discord.Game(name=result)
        # Setting `Listening ` status
        elif status == 2:
            random_num = random.uniform(0, 1) 
            if random_num >= 0.5: 
                async def fetch():
                    collection = MongoDB_DB.pjsk['songs']
                    songs = [song.get('songName', '') async for song in collection.find() if 'songName' in song]
                    return songs
                
                bot = get_bot()
                fut = asyncio.run_coroutine_threadsafe(fetch(), bot.loop)
                songs = fut.result(timeout=30)
                result = songs[random.randint(0, len(songs)-1)]
            else:
                song_type = 'emo'
                result = base_openai_chat(
                    prompt=f'基於搜尋，找`一首`有關 `{song_type}` 的歌，確保輸出時僅輸出歌曲的名稱，沒有其他攏言贅字', 
                    model=model, 
                    temperature=0.8,
                    system_prompt=system_prompt, 
                    is_enable_tools=True,
                    top_p=0.9,
                    no_extra_system_prompt=True
                )[1]
                result = translate(result)
                result = halfToFull(result).replace('。', '\n')
            cls.past_status.append((f'{cur_time} 正在聽 ' + result))
            activity = discord.Activity(type=discord.ActivityType.listening, name=result)
        # Setting `Watching ` status
        elif status == 3:
            result = base_openai_chat(
                prompt=f'基於搜尋，找`一部`隨機的`愛情`電影，確保輸出時僅輸出電影的名稱，沒有其他攏言贅字', 
                model=model, 
                temperature=0.8,
                system_prompt=system_prompt, 
                is_enable_tools=True,
                top_p=0.9,
                no_extra_system_prompt=True
            )[1]
            result = translate(result)
            result = halfToFull(result).replace('。', '\n')
            cls.past_status.append((f'{cur_time} 正在看 ' + result))
            activity = discord.Activity(type=discord.ActivityType.watching, name=result)

        return activity

def save_to_knowledge_base(prompt:str, assistant_prompt:str):
    '''會判斷是否要將此次對話之知識 存入本地知識庫當中，(由glm 4 flash做function calling然後判斷)。'''
    system_prompt = '''
    You are an intelligent assistant capable of extracting and saving useful knowledge from conversations.

    Your tasks are:

    1. If the user initiates any action such as a search, lookup, or query, and the system responds with information, you must evaluate whether the response contains useful and factual knowledge.

    2. If you find valuable, **factually accurate** information in the context, you must call the `knowledge_save` tool to save this information into the knowledge base.

    3. Only save information that meets the following criteria:
    - Does not include any personal information (e.g., names, age, address, contact info, user preferences)
    - Does not include **relative time references** (e.g., "yesterday", "last week", "tomorrow")
    - Must be **objective and accurate** (from a search result or user-provided fact)
    - Do not store subjective opinions, emotions, jokes, or speculative information
    4. Do not store users' personal information or preferences

    When saving:
    - `question`: the original user question
    - `answer`: your final factual response to that question
    - `tags`: a comma-separated list of keywords related to the topic (in English only)
    - `source`: the origin of the knowledge, such as a URL (if available); leave blank if none

    If you're unsure whether the information is accurate or valuable enough, **do NOT save it**.

    Do not store information automatically unless these conditions are met.
    Do not ask the user whether to store it — just decide by yourself.

    '''

    summarize_system_prompt = '''
    請根據前後文，將對話整理成包含question answer tags(Enter multiple keywords related to this question and its answers, with each keyword separated by a comma. source(the url of datas))
    輸出格式:
        question: ...
        answer: ...
        tags: ...
        source: ...
    '''

    history:list = to_user_message(prompt) + to_assistant_message(assistant_prompt)
    content = summarize(history, summarize_system_prompt)
    messages = to_system_message(system_prompt) + to_user_message(content)
    # print(messages)
    try:
        response = ollama.chat(
            model='MFDoom/deepseek-r1-tool-calling:8b',
            messages=messages,
            stream=False,
            tools=[tools_descrip[8]]
        )

        # 不需要tools則return
        if not response.message.tool_calls: print(f'本次對話沒有新增到資料庫當中。reason: {response.message.content[:100]}'); return
        else: print('新增資料庫中...')

        func_results = get_tool_results(response.message.tool_calls)
    except:
        print('An error accured when decide if save to knowledge bases.\n')
        traceback.print_exc()
        response = true_zhipu.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            tool_choice='auto',
            tools=[tools_descrip[8]],
            temperature=0.8
        )
        # print(response)
        if not response.choices[0].message.tool_calls: print(f'本次對話沒有新增到資料庫當中。reason: {response.choices[0].message.content[:100]}'); return
        else: print('新增資料庫中...')
    
        func_results = get_tool_results(response.choices[0].message.tool_calls)

class Preference:
    @staticmethod
    def get_preferences(userID) -> str:
        try:
            userID = int(userID)
            connection, cursor = user_preferences()
            cursor.execute('SELECT preference FROM preferences WHERE user_id = ?', (userID,))
            result = cursor.fetchone()
            connection.close()
            # print(result)
            if result: return ''.join(result)
            else: return ''
        except Exception as e:
            traceback.print_exc()
            print(f'Error in get_preferences: {e}')
            return ''
        
    @staticmethod
    def save_to_db(*, preference: str, userID: int):
        connection, cursor = user_preferences()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (userID,))
        result = cursor.fetchone()

        if result:
            # 如果存在，則更新
            preference += str(result[2])
            cursor.execute("UPDATE preferences SET preference = ? WHERE user_id = ?", (preference, userID))
        else:
            # 如果不存在，則插入
            cursor.execute("INSERT INTO preferences (user_id, preference) VALUES (?, ?)", (userID, preference))
        
        # 提交更改
        connection.commit()
        connection.close()

    @staticmethod
    def save_to_preferences(userID, messages: list):
        '''userID and messages's len = 2 (including user prompt and assistant prompt)'''
        system_prompt = '''
        You are an AI that can observe the conversation and identify key pieces of information related to the user's preferences, likes, dislikes, or habits. If the user provides any information that indicates their personal preferences, interests, or habits (e.g., favorite activities, hobbies, preferences for certain products, or how they like things), you should extract and save that information for future interactions. 

        When you encounter new preferences or important user information, mark them as relevant, and store them in a format that can be used for future interactions. This can include things like favorite foods, music genres, favorite games, or any other details that help make the conversation more personal. 

        Make sure to only store information that is relevant for personalizing the interaction and avoid storing sensitive or irrelevant details. Your task is to observe and extract preferences, and when identified, make note of them for future conversations.
        '''

        tool = {
            "type": "function",
            "function": {
                "name": "save_to_preferences",
                "description": "This tool is used to save some user's preference to databases, Every args should in English.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preference": {"type":"string", "description":"Enter some preference here. Use a string to describe the user's preference"},
                    },
                    "required": ['preference']
                }
            }
        }

        try:
            response = ollama.chat(
                model='nemotron-mini',
                messages=to_system_message(system_prompt) + messages,
                stream=False,
                tools=[tool]
            )

            # 不需要tools則return
            if not response.message.tool_calls: return
            else: print('新增使用者喜好中...')

            tool_call = response.message.tool_calls[0]

        except: 
            response = true_zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=to_system_message(system_prompt) + messages,
                tools = [tool]
            )

            if not response.choices[0].message.tool_calls: return
            else: print('新增使用者喜好中...')

            tool_call = response.choices[0].message.tool_calls[0]

        try:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments
            args = orjson.loads(arguments) if type(arguments) != dict else arguments
            print(f'{tool_name=}: {arguments=}')

            Preference.save_to_db(userID=userID, **args)
        except: traceback.print_exc()

class UserInfo:
    def __init__(self, userID: int):
        self.userID = userID
        connection, cursor = user_info()
        self.connection = connection
        self.cursor = cursor
    
    def get_info(self):
        try:
            userID = int(self.userID)
            connection, cursor = self.connection, self.cursor
            cursor.execute('SELECT info FROM infos WHERE user_id = ?', (userID,))
            result = cursor.fetchone()
            connection.close()
            # print(result)
            if result: return ''.join(result)
            else: return ''
        except Exception as e:
            traceback.print_exc()
            print(f'Error in get_info: {e}')
            return ''
        
    def save_to_db(self, *, info: str):
        try: userID = int(self.userID)
        except: traceback.print_exc(); return
        connection, cursor = self.connection, self.cursor
        cursor.execute("SELECT * FROM infos WHERE user_id = ?", (userID,))
        result = cursor.fetchone()
        preference = []

        if result:
            # 如果存在，則更新
            preference += result[2]
            cursor.execute("UPDATE infos SET info = ? WHERE user_id = ?", (info, userID))
        else:
            # 如果不存在，則插入
            cursor.execute("INSERT INTO infos (user_id, info) VALUES (?, ?)", (userID, info))
        
        # 提交更改
        connection.commit()
        connection.close()