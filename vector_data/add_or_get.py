'''參考連結: https://blog.csdn.net/BlueSocks152/article/details/146201160'''

# 导入所需库
import chromadb  # ChromaDB 向量数据库
from openai import OpenAI  # OpenAI 客户端

# 初始化 OpenAI 客户端 (替换成自己的 API 信息)
client = OpenAI(
    api_key="ollama",  # 替换为你的 OpenAI API Key , 这里我把自己的 API-KEY 隐藏了
    base_url="http://localhost:11434/v1"  # 替换为你的 API 服务端点
)

def get_embeddings(texts, model="nomic-embed-text"):
    """将文本转换为向量表示"""
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data]

def add(file_path: str = './vector_data/test.txt'):
    # 初始化 ChromaDB 客户端 (持久化到本地目录)
    chroma_client = chromadb.PersistentClient(path="./vector_data")

    # 创建或获取集合 (相当于数据库表)
    collection = chroma_client.get_or_create_collection(
        name="information",  # 集合名称
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )

    # 原始文本数据集 (示例新闻标题)
    # documents = [
    #     "李彦宏称大模型成本每年降低90%",  # 科技类
    #     "乌军大批直升机击落多架俄无人机",  # 国际争端
    #     "王力宏回应是否想找新伴侣",  # 娱乐新闻
    #     "饺子不知道观众怎么想出的藕饼cp",  # 影视相关
    #     "加沙停火协议关键时刻生变"  # 国际争端
    # ]
    with open(file_path, mode='r', encoding='utf8') as f:
        texts = f.read()
    documents = texts.split('。')

    # 批量生成文档向量 (OpenAI API调用)
    document_embeddings = get_embeddings(documents)

    # 生成唯一文档 ID (需要唯一标识符)
    document_ids = [str(i) for i in range(len(documents))]  # 生成 ["0", "1", ..., "4"]

    # 将文档插入数据库
    collection.add(
        ids=document_ids,  # 唯一ID列表
        embeddings=document_embeddings,  # 文本向量列表
        documents=documents  # 原始文本列表
    )
    # collection.delete(ids=[] or None)

def get(query: str):
    chroma_client = chromadb.PersistentClient(path="./vector_data")
    collection = chroma_client.get_or_create_collection(
        name="information",
        metadata={"hnsw:space": "cosine"}
    )
    query_embedding = get_embeddings([query])[0]
    search_results = collection.query(
        query_embeddings=[query_embedding], 
        n_results=2  
    )
    # This is a result including 2 search results
    results = search_results['documents'][0]
    return results

if __name__ == '__main__':
    add("test.txt")
