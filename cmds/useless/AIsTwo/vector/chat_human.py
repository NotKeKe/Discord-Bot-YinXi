import chromadb
from chromadb.api.models.Collection import Collection
import re
import traceback

from cmds.AIsTwo.vector import utils

def create() -> Collection:
    chroma_client = chromadb.PersistentClient(path="./cmds/AIsTwo/vector/data")

    # 创建或获取集合 (相当于数据库表)
    collection = chroma_client.get_or_create_collection(
        name="data",  # 聊天風格範本
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )
    return collection

def split(text: str) -> list:
    # 将文本分割成多个片段
    return re.split(r"\n\n|[。!?！？]", text)

async def add(collection: Collection, data_path: str = None, text: str = None):
    # 加载数据文件并添加到集合中
    if data_path:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = f.read()
    else:
        data = [text]

    documents = split(data)
    ids = [str(i) for i in range(len(documents))]
    documents_embedding = await utils.async_get_embeddings(documents)
    print(len(documents_embedding))
    print(documents_embedding)

    collection.add(
        ids=ids,
        embeddings=documents_embedding,
        documents=documents
    )

async def async_get(collection: Collection, query: str, top_k: int = 2) -> list:
    try:
        query_embedding = (await utils.async_get_embeddings([query]))
        search_results = collection.query(
            query_embeddings=[query_embedding], 
            n_results=top_k
        )
        # This is a result including 2 search results
        results = search_results['documents'][0]
        return results
    except:
        traceback.print_exc()
        return ['None']

def get(collection: Collection, query: str, top_k: int = 2) -> list:
    try:
        query_embedding = utils.get_embeddings([query])[0]
        search_results = collection.query(
            query_embeddings=[query_embedding], 
            n_results=top_k
        )
        # This is a result including 2 search results
        results = search_results['documents'][0]
        return results
    except:
        # traceback.print_exc()
        return ['None']

async def delete(collection: Collection, ids: list[int]):
    collection.delete(ids=ids)