from openai import AsyncOpenAI, OpenAI

from .config import base_url_options

class AsyncClient:
    openrouter = AsyncOpenAI(
        base_url=base_url_options['openrouter']['base_url'],
        api_key=base_url_options['openrouter']['api_key']
    )

    zhipu = AsyncOpenAI(
        base_url=base_url_options['zhipu']['base_url'],
        api_key=base_url_options['zhipu']['api_key']
    )

    ollama = AsyncOpenAI(
        base_url=base_url_options['ollama']['base_url'],
        api_key=base_url_options['ollama']['api_key']
    )

    gemini = AsyncOpenAI(
        base_url=base_url_options['gemini']['base_url'],
        api_key=base_url_options['gemini']['api_key']
    )

    cerebras = AsyncOpenAI(
        base_url=base_url_options['cerebras']['base_url'],
        api_key=base_url_options['cerebras']['api_key']
    )

    lmstudio = AsyncOpenAI(
        base_url=base_url_options['lmstudio']['base_url'],
        api_key=base_url_options['lmstudio']['api_key']
    )

class SyncClient:
    openrouter = OpenAI(
        base_url=base_url_options['openrouter']['base_url'],
        api_key=base_url_options['openrouter']['api_key']
    )

    zhipu = OpenAI(
        base_url=base_url_options['zhipu']['base_url'],
        api_key=base_url_options['zhipu']['api_key']
    )

    ollama = OpenAI(
        base_url=base_url_options['ollama']['base_url'],
        api_key=base_url_options['ollama']['api_key']
    )

    gemini = OpenAI(
        base_url=base_url_options['gemini']['base_url'],
        api_key=base_url_options['gemini']['api_key']
    )

    cerebras = OpenAI(
        base_url=base_url_options['cerebras']['base_url'],
        api_key=base_url_options['cerebras']['api_key']
    )

    lmstudio = OpenAI(
        base_url=base_url_options['lmstudio']['base_url'],
        api_key=base_url_options['lmstudio']['api_key']
    )
