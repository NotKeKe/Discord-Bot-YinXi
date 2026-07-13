USER_DAILY_TOKEN_LIMIT: int = 500_000

USER_PROVIDER_RATE: dict[str, tuple[int, int]] = {
    "zhipu":      (20, 60),
    "openrouter": (10, 60),
    "gemini":     (10, 60),
    "cerebras":   (15, 60),
    "ollama":     (30, 60),
    "lmstudio":   (30, 60),
    "ai-local":   (30, 60),
}
USER_PROVIDER_RATE_DEFAULT: tuple[int, int] = (20, 60)

USER_MODEL_RATE: dict[str, dict[str, tuple[int, int]]] = {
    "zhipu": {
        "glm-4-flash": (10, 60),
        "glm-4-plus":  (2, 60),
    },
    "gemini": {
        "gemini-2.0-flash": (5, 60),
    },
}

PROVIDER_CONCURRENCY: dict[str, int] = {
    "openrouter": 3,
    "zhipu":      5,
    "ollama":     8,
    "gemini":     3,
    "cerebras":   5,
    "lmstudio":   8,
    "ai-local":   8,
}
