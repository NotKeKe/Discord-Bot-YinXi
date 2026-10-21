"""`cmds/cambridge_channel.py`：每日單字測驗的出題邏輯（不連網）。"""

from __future__ import annotations

import importlib
import random
from typing import Any

import pytest

from tests.helpers import FakeCollection


class FakeDB:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.collection = FakeCollection(docs=docs)

    def __getitem__(self, key: str) -> Any:
        return self.collection


def _make_doc(index: int, word: str) -> dict[str, Any]:
    return {
        "word": word,
        "meanings": [f"{word} 的意思"],
        "examples": [{"eg": f"I really like {word} today.", "translate": f"我今天很喜歡 {word}"}],
        "create_at": index,
    }


DOCS = [_make_doc(index, word) for index, word in enumerate(["apple", "banana", "cherry", "dragon", "elder", "fig"])]


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.cambridge_channel")


@pytest.fixture
def fake_db(module: Any, monkeypatch: pytest.MonkeyPatch) -> FakeDB:
    db = FakeDB(DOCS)
    monkeypatch.setattr(module, "db", db)
    return db


@pytest.mark.asyncio
async def test_get_random_test_requires_enough_documents(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "db", FakeDB(DOCS[:5]))

    assert await module._get_random_test(1) is None


@pytest.mark.asyncio
async def test_get_random_test_blanks_the_word(module: Any, fake_db: FakeDB) -> None:
    random.seed(0)

    result = await module._get_random_test(1)

    assert result is not None
    word, meanings, eg_sentence, translate_sentence, wrong_datas = result
    assert word in {doc["word"] for doc in DOCS}
    assert meanings
    assert "_" in eg_sentence
    assert word.lower() not in eg_sentence.lower()
    assert translate_sentence
    assert len(wrong_datas) == 3
    assert all("word" in doc for doc in wrong_datas)


@pytest.mark.asyncio
async def test_generate_daily_test_builds_four_options(module: Any, fake_db: FakeDB) -> None:
    random.seed(42)

    embed, view, description = await module.gener_daily_test(1)

    assert embed.title == "Daily Test!!!"
    options = [line for line in description.splitlines() if line[:2] in ("A.", "B.", "C.", "D.")]
    assert len(options) == 4
    assert len({line[3:] for line in options}) == 4
    assert len(view.children) == 4
    answers = {line[3:] for line in options}
    assert answers & {doc["word"] for doc in DOCS}


@pytest.mark.asyncio
async def test_generate_daily_test_without_data(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "db", FakeDB(DOCS[:5]))

    embed, view, description = await module.gener_daily_test(1)

    assert description == ""
    assert embed.title is None
    assert len(view.children) == 0
