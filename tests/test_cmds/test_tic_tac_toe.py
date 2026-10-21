"""`cmds/tic_tac_toe.py`：棋局邏輯與按鈕互動。"""

from __future__ import annotations

import importlib
from typing import Any, Iterator

import pytest

from tests.helpers import make_ctx, make_interaction
from tests.helpers import last_call

CHANNEL_ID = 55
X = ":x:"
O = ":blue_circle:"
EMPTY = ":new_moon:"

WIN_CASES = [
    pytest.param([(0, 0), (0, 1), (0, 2)], X, id="row-0"),
    pytest.param([(1, 0), (1, 1), (1, 2)], O, id="row-1"),
    pytest.param([(2, 0), (2, 1), (2, 2)], X, id="row-2"),
    pytest.param([(0, 0), (1, 0), (2, 0)], O, id="col-0"),
    pytest.param([(0, 1), (1, 1), (2, 1)], X, id="col-1"),
    pytest.param([(0, 2), (1, 2), (2, 2)], O, id="col-2"),
    pytest.param([(0, 0), (1, 1), (2, 2)], X, id="diagonal"),
    pytest.param([(0, 2), (1, 1), (2, 0)], O, id="anti-diagonal"),
]


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.tic_tac_toe")


@pytest.fixture
def game(module: Any) -> Any:
    return module.TicTacToeGame()


@pytest.fixture
def cog(bot: Any, module: Any) -> Iterator[Any]:
    instance = module.TicTacToe(bot)
    try:
        yield instance
    finally:
        instance.games.clear()


def test_new_board_is_empty(game: Any) -> None:
    assert game.board == [[EMPTY, EMPTY, EMPTY] for _ in range(3)]
    assert game.current_player == X
    assert game.format_board().count("\n") == 2


@pytest.mark.parametrize("cells,winner", WIN_CASES)
def test_check_winner(game: Any, cells: list[tuple[int, int]], winner: str) -> None:
    for row, col in cells:
        game.board[row][col] = winner

    assert game.check_winner() == winner


def test_check_winner_draw(game: Any) -> None:
    game.board = [
        [X, O, X],
        [X, O, O],
        [O, X, X],
    ]

    assert game.check_winner() is None


def test_format_board_contains_all_cells(game: Any) -> None:
    game.board[0][0] = "  :x:  "

    first_line = game.format_board().splitlines()[0]

    assert first_line == "  :x:   | :new_moon: | :new_moon:"


@pytest.mark.asyncio
async def test_start_game_creates_board_and_view(cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot, channel_id=CHANNEL_ID)

    await cog.start_game.callback(cog, ctx)

    assert CHANNEL_ID in cog.games
    kwargs = last_call(ctx.send).kwargs
    assert kwargs["embed"].description == cog.games[CHANNEL_ID].format_board()
    buttons = kwargs["view"].children
    assert len(buttons) == 9
    assert {button.custom_id for button in buttons} == {
        f"{CHANNEL_ID}-{row}-{col}" for row in range(3) for col in range(3)
    }


@pytest.mark.asyncio
async def test_click_places_mark_and_switches_player(cog: Any, module: Any) -> None:
    game = module.TicTacToeGame()
    cog.games[CHANNEL_ID] = game
    interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-0-0"})

    await cog.on_interaction(interaction)

    assert game.board[0][0] == f"  {X}  "
    assert game.moves[X] == [(0, 0)]
    assert game.current_player == O
    interaction.response.edit_message.assert_awaited_once()
    assert len(last_call(interaction.response.edit_message).kwargs["view"].children) == 9


@pytest.mark.asyncio
async def test_click_on_taken_position_warns(cog: Any, module: Any) -> None:
    game = module.TicTacToeGame()
    game.board[0][0] = f"  {X}  "
    game.moves[X] = [(0, 0)]
    cog.games[CHANNEL_ID] = game
    interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-0-0"})

    await cog.on_interaction(interaction)

    interaction.response.send_message.assert_awaited_once()
    assert last_call(interaction.response.send_message).kwargs["ephemeral"] is True
    interaction.response.edit_message.assert_not_awaited()
    assert game.board[0][0] == f"  {X}  "


@pytest.mark.asyncio
async def test_click_without_game(cog: Any) -> None:
    interaction = make_interaction(data={"component_type": 2, "custom_id": "999-0-0"})

    await cog.on_interaction(interaction)

    interaction.response.send_message.assert_awaited_once()
    assert last_call(interaction.response.send_message).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_non_button_interaction_is_ignored(cog: Any) -> None:
    interaction = make_interaction(data={"component_type": 3, "custom_id": f"{CHANNEL_ID}-0-0"})

    await cog.on_interaction(interaction)

    interaction.response.edit_message.assert_not_awaited()
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_malformed_custom_id_is_ignored(cog: Any) -> None:
    interaction = make_interaction(data={"component_type": 2, "custom_id": "not-a-number"})

    await cog.on_interaction(interaction)

    interaction.response.edit_message.assert_not_awaited()
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_winning_move_ends_game(cog: Any, bot: Any) -> None:
    cog.games[CHANNEL_ID] = importlib.import_module("cmds.tic_tac_toe").TicTacToeGame()
    moves = ["0-0", "1-1", "0-1", "1-0", "0-2"]

    for move in moves:
        interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-{move}"})
        await cog.on_interaction(interaction)
        last = interaction

    assert CHANNEL_ID not in cog.games
    assert last_call(last.response.edit_message).kwargs["view"] is None
    description = last_call(last.response.edit_message).kwargs["embed"].description
    assert "|" in description


@pytest.mark.asyncio
async def test_oldest_mark_rolls_out_after_three_moves(cog: Any, module: Any) -> None:
    """同一玩家放滿 3 顆後，最舊的一顆會被替換成 :heavy_multiplication_x:。"""

    game = module.TicTacToeGame()
    cog.games[CHANNEL_ID] = game

    for move in ["0-0", "1-1", "0-1", "1-0", "0-2"]:
        interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-{move}"})
        await cog.on_interaction(interaction)

    # 重新開一局，驗證「X 第 3 子後，O 落子時會把 X 最舊的棋子換掉」
    game = module.TicTacToeGame()
    cog.games[CHANNEL_ID] = game
    for move in ["0-0", "1-1", "0-1", "1-0"]:
        interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-{move}"})
        await cog.on_interaction(interaction)

    # 現在輪到 X（移動數 X=2, O=2），X 下第 3 子（不連線）
    interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-2-2"})
    await cog.on_interaction(interaction)

    # 輪到 O：O 的對手（X）已有 3 子，最舊的 (0,0) 會被替換
    interaction = make_interaction(data={"component_type": 2, "custom_id": f"{CHANNEL_ID}-2-1"})
    await cog.on_interaction(interaction)

    assert game.board[0][0] == ":heavy_multiplication_x:"
