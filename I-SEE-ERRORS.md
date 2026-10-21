# I-SEE-ERRORS

測試與整理 `cmds/` 指令時發現的問題。原則：**能在測試側隔離的就只在測試側處理**，
需要動到 `core/`、`cmds/` 的一律先記錄、取得同意後才改。

## 已解決

### 1. locale 缺 key（2026-10-21 補齊）

`cmds/` 用到但 `core/locales/{en-US,zh-TW,zh-CN}.json` 三個語系都缺的 key，
會讓使用者直接看到 key 名稱。已補上（每個語系 12 個）：

| 區塊 | 補上的 key |
|---|---|
| `name` | `change_status_str`、`codlin_meme`、`petpet` |
| `description` | `change_status_str`、`codlin_meme`、`petpet`、`tictactoe_description` |
| `params_desc` | `lang_lang` |
| `components` | `qrcode_scanner_invalid_image`、`send_petpet_no_image`、`send_report_trace_not_exist`、`send_world_chat` |

- 其中 `send_world_chat` 是 `cmds/world_chat.py` 轉發圖片時 `load_translated()` 的來源，
  補上後「有附件的訊息」已能正常轉發到其他世界頻道。
- 回歸測試：`tests/test_cmds/test_locale_keys.py`（用 AST 掃出 `get_translate()`／`locale_str()`
  的 key，逐語系比對，避免之後又漏）。

### 2. `cmds/play4.py` 缺少 `websockets`

- 位置：`cmds/music_bot/play4/player.py:9` `import websockets`
  （使用點同檔 `222`、`244`，連 `ws://api_server:3000/player/dc/...`）。
- 已在同一工作期間把 `websockets>=17.3` 加入 `pyproject.toml`／`uv.lock`。
- 現在 `cmds.play4` 可正常 import，已納入 setup 契約測試與 `tests/test_cmds/test_music/test_play4.py`。

## 未解決

### 3. `cmds/world_chat.py`：純文字訊息不會被轉發

- 位置：`cmds/world_chat.py:54-71`
- 現況：整個「轉發到其他頻道」的區塊都在 `if attachments:` 裡面，**沒有附件時什麼都不送**
  （只有 `History` 仍會寫入）。有附件的訊息在補上 `send_world_chat` 後已正常。
- 影響測試：`test_world_chat.py::test_message_is_forwarded_to_other_channels` 以
  `xfail(strict=True)` 標記。

### 4. `cmds/bot_info_help.py`：`/help` 未指定 cog 時的指令自動完成會拋錯

- 位置：`cmds/bot_info_help.py:93-95`
- 現況：`cmds = bot.commands` 是 `dict`，下一行 `[c.name for c in cmds]` 迭代到 key（`str`）
  → `AttributeError`。指定 `cog_name` 時 `cog.get_commands()` 是 list，正常。
- 影響測試：`test_bot_info_help.py` 的兩個「未指定 cog」案例以 `xfail(strict=True)` 標記。

### 5. 裸跑 `pytest` 會收集 `cmds/data.json/data_test.py`

- 位置：`cmds/data.json/data_test.py:13`
- 現況：檔名符合 pytest 預設 `*_test.py`，被收集後在 import 時開檔
  `./cmds/cmds/data.json/skyblock_bazaar_item_tracker.txt`（多一層）→ `FileNotFoundError`，
  整個 collection 中斷。
- 目前處置：根目錄 `pytest.ini` 設 `testpaths = tests`、`python_files = test_*.py`，未動 `cmds/`。

### 6. `cmds/qrcode.py`：Windows 上 `/qrcode_generator` 會 `PermissionError`

- 位置：`cmds/qrcode.py:48-49`
- 現況：`discord.File(path)` 先開啟檔案，接著 `os.remove(path)`；Windows 不允許刪除被開啟的檔案
  （`WinError 32`）→ `PermissionError`。Linux 部署環境沒有這個問題。
- 影響測試：`test_qrcode.py` 以假的 `discord.File` 驗證流程（含刪除暫存檔），未修改 `cmds/qrcode.py`。
