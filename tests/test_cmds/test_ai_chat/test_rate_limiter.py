import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from cmds.ai_chat.v2.rate_limiter.main import (
    RateLimitExceeded,
    _ProviderConcurrencyController,
    RateLimiter,
)


# ─── Layer 3: _ProviderConcurrencyController ───

@pytest.mark.asyncio
async def test_concurrency_limits_acquire():
    ctrl = _ProviderConcurrencyController(max_concurrent=2)

    acquired = []

    async def worker(tag):
        await ctrl.acquire(is_admin=False)
        acquired.append(tag)
        await asyncio.sleep(0.05)
        ctrl.release()

    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.sleep(0.01)

    assert len(acquired) == 2

    await asyncio.gather(*tasks)
    assert acquired == [0, 1, 2]


@pytest.mark.asyncio
async def test_admin_priority_in_queue():
    ctrl = _ProviderConcurrencyController(max_concurrent=1)

    order = []

    async def worker(tag):
        await ctrl.acquire(is_admin=(tag == "admin"))
        order.append(tag)
        await asyncio.sleep(0.02)
        ctrl.release()

    user1 = asyncio.create_task(worker("user1"))
    await asyncio.sleep(0.01)

    user2 = asyncio.create_task(worker("user2"))
    admin = asyncio.create_task(worker("admin"))
    await asyncio.sleep(0.01)

    await user1
    await asyncio.sleep(0.01)
    await asyncio.gather(user2, admin)

    assert order == ["user1", "admin", "user2"]


@pytest.mark.asyncio
async def test_release_with_no_waiters():
    ctrl = _ProviderConcurrencyController(max_concurrent=1)
    await ctrl.acquire(False)
    ctrl.release()
    ctrl.release()


# ─── Shared fixtures for RateLimiter tests ───

@pytest.fixture
def mock_daily_col():
    return MagicMock(
        find_one=AsyncMock(),
        update_one=AsyncMock(),
        create_index=AsyncMock(),
    )


@pytest.fixture
def rl_with_mock(mock_daily_col):
    rl = object.__new__(RateLimiter)
    RateLimiter.__init__(rl)
    rl._daily_col = mock_daily_col
    rl._indexes_ready = True
    return rl


# ─── Layer 1: MongoDB token counting ───

@pytest.mark.asyncio
async def test_daily_under_limit(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 5000})
    await rl_with_mock._check_daily_allowed(12345)


@pytest.mark.asyncio
async def test_daily_first_request(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value=None)
    await rl_with_mock._check_daily_allowed(12345)


@pytest.mark.asyncio
async def test_daily_over_limit(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 999_999})
    with pytest.raises(RateLimitExceeded):
        await rl_with_mock._check_daily_allowed(12345)


@pytest.mark.asyncio
async def test_record_usage_adds_tokens(rl_with_mock, mock_daily_col):
    mock_daily_col.update_one = AsyncMock()
    await rl_with_mock.record_usage(12345, 500)

    mock_daily_col.update_one.assert_called_once()
    args, kwargs = mock_daily_col.update_one.call_args
    assert args[0]["user_id"] == 12345
    assert "date" in args[0]
    assert args[1] == {"$inc": {"tokens": 500}}
    assert kwargs == {"upsert": True}


@pytest.mark.asyncio
async def test_record_usage_skips_zero(rl_with_mock, mock_daily_col):
    mock_daily_col.update_one = AsyncMock()
    await rl_with_mock.record_usage(12345, 0)
    mock_daily_col.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_record_usage_skips_negative(rl_with_mock, mock_daily_col):
    mock_daily_col.update_one = AsyncMock()
    await rl_with_mock.record_usage(12345, -1)
    mock_daily_col.update_one.assert_not_called()


# ─── Admin bypass ───

@pytest.mark.asyncio
async def test_admin_skips_daily_check(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 999_999})
    await rl_with_mock._acquire(12345, "zhipu", "glm-4-flash", is_admin=True)
    rl_with_mock._release("zhipu")


@pytest.mark.asyncio
async def test_normal_user_blocked_over_daily(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 999_999})
    with pytest.raises(RateLimitExceeded):
        await rl_with_mock._acquire(12345, "zhipu", "glm-4-flash", is_admin=False)


# ─── Full flow ───

@pytest.mark.asyncio
async def test_normal_user_acquire_release(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 100})
    await rl_with_mock._acquire(12345, "zhipu", "glm-4-flash", is_admin=False)
    rl_with_mock._release("zhipu")


@pytest.mark.asyncio
async def test_async_with_context_manager(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 100})

    async with rl_with_mock(
        user_id=12345,
        provider="zhipu",
        model="glm-4-flash",
        is_admin=False,
    ):
        pass

    mock_daily_col.update_one = AsyncMock()
    await rl_with_mock.record_usage(12345, 200)
    mock_daily_col.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_lru_limiter_cleanup(rl_with_mock, mock_daily_col):
    mock_daily_col.find_one = AsyncMock(return_value={"tokens": 100})

    for i in range(1005):
        provider = f"prov_{i}"
        await rl_with_mock._acquire(12345, provider, "m", is_admin=False)
        rl_with_mock._release(provider)

    assert len(rl_with_mock._user_provider_limiters) <= rl_with_mock._MAX_LIMITERS
