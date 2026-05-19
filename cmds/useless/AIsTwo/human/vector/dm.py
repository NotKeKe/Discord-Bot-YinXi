'''
普通使用僅使用 save() and search()就好
預留 6 則對話 (不包括 system promot)
'''

from asyncio import to_thread
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from chromadb.api.models.Collection import Collection
from typing import List, Tuple
from uuid import uuid4
from datetime import datetime, timezone
from discord import Message
from pprint import pp

from cmds.AIsTwo.utils import to_assistant_message, to_user_message
from core.functions import BASE_OLLAMA_URL, UnixNow, UnixToReadable

client = chromadb.PersistentClient(
    './data/dm_chat/histories'
)

eb_func = OllamaEmbeddingFunction(
    url=BASE_OLLAMA_URL,
    model_name='nomic-embed-text'
)

def process_messages(messages: List[dict]) -> List[str]:
    """
    將訊息處理成適合 embedding 的格式

    Args:
        messages (List[dict]): 此處大小應該為 6，且最後一則為 assistant
        [
            {
                "role": "user",
                "content": "「使用者ID: 703877871256731678，使用者名稱: 克克 KeJC」說了: `幹嘛`"
            },
            {
                "role": "assistant",
                "content": "..."
            }
        ]

    Returns:
        List[str]: 用來放在embeddings的messages
        [
            "user: I'm looking for a job., assistant: Hello! How can I assist you today?",
            "user: anfjawfbnuwjafn, assistant: I'm here to help you find a job. What kind of job are you interested in?"
            ...
        ]
    """    
    result = []
    for i in range(0, 6, 2):
        user_content = messages[i]['content']
        assistant_content = messages[i+1]['content']
        result.append(f'user: {user_content} assistant: {assistant_content}')

    return result

def gener_ids(channel_id: str, documents: List[str]) -> List[int]:
    result = []
    for _ in range(len(documents)):
        uuid = uuid4().hex[:6]
        result.append(f'{channel_id}_{uuid}_{UnixNow()}')

    return result

async def get_collection(channel_id: str) -> Collection:
    def get():
        collection = client.get_or_create_collection(
            name=channel_id,
            embedding_function=eb_func,
            metadata={"hnsw:space": "cosine"}
        )
        return collection
    return await to_thread(get)

async def save(channel_id: str, messages: List[dict]) -> None:
    """儲存 user + assistant 的聊天記錄到 ChromaDB 中。

    Args:
        channel_id (str): The user's id in discord.
        messages (List[dict]): It should include user's query + assistant's response. 
    """    
    # print('save')
    collection = await get_collection(channel_id)
    processed_messages = process_messages(messages)
    def savee():
        ids = gener_ids(channel_id, processed_messages)
        collection.add(
            ids=ids,
            documents=processed_messages,
            metadatas=[{"time": UnixNow()} for _ in ids]
        )

    await to_thread(savee)

async def search(query: str, channel_id: str, n_result: int = 5) -> str:
    collection = await get_collection(channel_id)
    def search_query():
        results = collection.query(
            query_texts=[query],
            n_results=n_result
        )
        return results
    results = await to_thread(search_query)

    search_results = []

    for i, (doc, meta, dist) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        if 'last_save' in meta: continue
        id = results['ids'][0][i]
        time = UnixToReadable(meta['time'])
        content = f"<history #{i+1} id={id} similarity={1-dist:.4f} time={time}>{doc}</history>"
        search_results.append(content)

    return '\n'.join(search_results) if search_results else ""


def find_message_position(
    messages: List[Message], 
    target_user: str, 
    target_timestamp: str
) -> int:
    """
    在消息列表中查找符合条件的位置
    Created by DeepSeek and Gemini
    
    Args:
        messages: 消息列表（按时间升序排列）
        target_user: 要匹配的用户对象（用户或机器人）
        target_timestamp: 目标时间戳（ISO格式字符串）
    
    Returns:
        如果找到符合条件的消息且后续消息>=6条，返回消息位置索引
        否则返回None
    """
    try:
        target_time = datetime.fromtimestamp(float(target_timestamp), tz=timezone.utc)
    except ValueError as e:
        # print(f'Invalid timestamp format. {e}')
        return None

    # 确保消息列表按时间升序排列
    # sorted_messages = messages.reverse()
    
    for i, msg in enumerate(messages):
        # 检查用户匹配（用户或机器人）
        is_user_match = msg.author.bot is (target_user == 'assistant')
        
        # 检查时间戳是否接近（允许±5秒误差）
        msg_time = msg.created_at.astimezone(timezone.utc)
        time_diff = abs((msg_time - target_time).total_seconds())
        
        if is_user_match and time_diff <= 5:
            # 检查后续消息数量是否>=6
            if len(messages) - i - 1 >= 6:
                return i
            break
    
    return None

async def create_final_save_timestamp(channel_id: str, from_type: str):
    if from_type not in ('user', 'assistant'): raise ValueError('Invaild user/assistant')

    timestamp = str(datetime.now().timestamp())
    collection = await get_collection(channel_id)

    def add():
        collection.add(
            documents=['a'],
            metadatas=[{
                'id': channel_id,
                'last_save': timestamp,
                'from_type': from_type
            }],
            ids=['a']
        )

    def update():
        collection.update(
            ids=['a'],
            documents=['a'],
            metadatas=[{
                'id': channel_id,
                'last_save': timestamp,
                'from_type': from_type
            }]
        )

    def get():
        r = collection.get(
            ids=['a']
        )
        if r['ids']:
            update()
        else:
            add()
    
    await to_thread(get)

async def get_final_save_timestamp(channel_id: str) -> Tuple[str, str]:
    collection = await get_collection(channel_id)
    def get():
        result = collection.get(
            where={'last_save': {'$ne': "__NON_EXISTENT__"}},
            include=["metadatas"]
        )
        if not result['metadatas']:
            return '', ''
        # pp(result)
        for item in result['metadatas']:
            if not ( 'last_save' in item and 'from_type' in item ): continue
            return item['last_save'], item['from_type']
        return '', ''
    
    return await to_thread(get)

async def to_vector_data(channel_id: str, msg: Message):
    # print('running to_vector_data')

    timestamp, from_type = await get_final_save_timestamp(str(channel_id))

    messages = [m async for m in msg.channel.history(limit=20)]
    if len(messages) < 12: 
        # print('return running to_vector_data1')
        return
    messages.reverse()
    if not find_message_position(messages, target_user=from_type, target_timestamp=timestamp) and timestamp:
        # print('return running to_vector_data2')
        return

    result = []
    pre = str()
    for m in messages:
        if not m.content: continue
        if m.author.bot:
            if m.content == '嘗試重啟bot...': continue
            if pre == 'bot':
                result[-1]['content'] += m.content + '\n'
            else:
                result.extend(to_assistant_message(m.content + '\n'))
            pre = 'bot'
        else:
            if m.content.startswith('['): continue
            if pre == 'user':
                result[-1]["content"] += m.content + '\n'
            else:
                content = '{userName} said: {mcontent}'.format(
                    userName=m.author.global_name, 
                    mcontent=m.content
                )
                result.extend(to_user_message(content + '\n'))
            pre = 'user'
    if len(result) < 12: return

    to_vector_data = result[-12:-6] # 注入到 vector data中
    await save(str(channel_id), to_vector_data)

    await create_final_save_timestamp(str(channel_id), to_vector_data[-1]['role'])