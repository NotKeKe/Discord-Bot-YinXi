import asyncio
import logging
from collections import OrderedDict

from aiolimiter import AsyncLimiter

from core.functions import current_datetime
from core.mongodb import MongoDB_DB
from .config import (
    USER_DAILY_TOKEN_LIMIT,
    USER_PROVIDER_RATE,
    USER_PROVIDER_RATE_DEFAULT,
    USER_MODEL_RATE,
    PROVIDER_CONCURRENCY,
)

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class _ProviderConcurrencyController:
    def __init__(self, max_concurrent: int):
        self._max = max_concurrent
        self._active = 0
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

    async def acquire(self, is_admin: bool) -> None:
        if self._active < self._max:
            self._active += 1
            return
        event = asyncio.Event()
        priority = 0 if is_admin else 1
        await self._queue.put((priority, event))
        await event.wait()
        self._active += 1

    def release(self) -> None:
        self._active -= 1
        try:
            _, event = self._queue.get_nowait()
            event.set()
            self._active += 1
        except asyncio.QueueEmpty:
            pass


class _AcquireContext:
    def __init__(
        self,
        limiter: "RateLimiter",
        user_id: int,
        provider: str,
        model: str,
        is_admin: bool,
    ):
        self._limiter = limiter
        self._user_id = user_id
        self._provider = provider
        self._model = model
        self._is_admin = is_admin

    async def __aenter__(self):
        await self._limiter._acquire(
            self._user_id,
            self._provider,
            self._model,
            self._is_admin,
        )
        return self

    async def __aexit__(self, *args):
        self._limiter._release(self._provider)


class RateLimiter:
    def __init__(self):
        self._concurrency_controllers: dict[str, _ProviderConcurrencyController] = {}
        self._user_provider_limiters: OrderedDict[str, AsyncLimiter] = OrderedDict()
        self._user_model_limiters: OrderedDict[str, AsyncLimiter] = OrderedDict()
        self._MAX_LIMITERS = 1000
        self._daily_col = MongoDB_DB.rate_limit_daily

        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        try:
            await self._daily_col.create_index(
                [("user_id", 1), ("date", 1)],
                unique=True,
            )
            await self._daily_col.create_index(
                [("date", 1)],
                expireAfterSeconds=86400 * 7,
            )
        except Exception:
            logger.warning("rate_limit_daily indexes may already exist", exc_info=True)
        self._indexes_ready = True

    def __call__(
        self,
        *,
        user_id: int,
        provider: str,
        model: str,
        is_admin: bool = False,
    ) -> _AcquireContext:
        return _AcquireContext(self, user_id, provider, model, is_admin)

    async def _check_daily_allowed(self, user_id: int) -> None:
        await self._ensure_indexes()
        today = current_datetime().strftime("%Y-%m-%d")
        doc = await self._daily_col.find_one(
            {"user_id": user_id, "date": today},
        )
        current = doc["tokens"] if doc else 0
        if current >= USER_DAILY_TOKEN_LIMIT:
            raise RateLimitExceeded(
                f"今日 token 用量已達上限 ({USER_DAILY_TOKEN_LIMIT:,})"
            )

    async def record_usage(self, user_id: int, tokens: int) -> None:
        if tokens <= 0:
            return
        today = current_datetime().strftime("%Y-%m-%d")
        await self._daily_col.update_one(
            {"user_id": user_id, "date": today},
            {"$inc": {"tokens": tokens}},
            upsert=True,
        )

    def _get_or_create_limiter(
        self,
        key: str,
        cache: OrderedDict[str, AsyncLimiter],
        rate_config: tuple[int, int],
    ) -> AsyncLimiter:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        max_calls, window = rate_config
        limiter = AsyncLimiter(max_calls, window)
        cache[key] = limiter
        if len(cache) > self._MAX_LIMITERS:
            cache.popitem(last=False)
        return limiter

    def _get_controller(self, provider: str) -> _ProviderConcurrencyController:
        if provider not in self._concurrency_controllers:
            max_conc = PROVIDER_CONCURRENCY.get(provider, 5)
            self._concurrency_controllers[provider] = _ProviderConcurrencyController(max_conc)
        return self._concurrency_controllers[provider]

    async def _acquire(
        self,
        user_id: int,
        provider: str,
        model: str,
        is_admin: bool,
    ) -> None:
        if not is_admin:
            await self._check_daily_allowed(user_id)

        if not is_admin:
            limiter_a = self._get_or_create_limiter(
                f"{user_id}:{provider}",
                self._user_provider_limiters,
                USER_PROVIDER_RATE.get(provider, USER_PROVIDER_RATE_DEFAULT),
            )
            await limiter_a.acquire()

        if not is_admin:
            model_rate = USER_MODEL_RATE.get(provider, {}).get(model)
            if model_rate is not None:
                limiter_b = self._get_or_create_limiter(
                    f"{user_id}:{provider}:{model}",
                    self._user_model_limiters,
                    model_rate,
                )
                await limiter_b.acquire()

        controller = self._get_controller(provider)
        await controller.acquire(is_admin)

    def _release(self, provider: str) -> None:
        self._get_controller(provider).release()
