from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="ollama",
    base_url='http://192.168.31.199:11434/v1'
)

async def get_embeddings(texts, model="nomic-embed-text") -> list[float]:
    """将文本转换为向量表示"""
    response = await client.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data][0]