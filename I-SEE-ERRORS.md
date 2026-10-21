# I-SEE-ERRORS

測試 `cmds/` 指令時發現、但**依指示不修改** `core/` 與 `cmds/` 的既有問題。
以下每一項都已用測試或探測確認過；測試套件不會因為這些問題而紅燈
（需要修的問題以 `xfail(strict=True)` 標記，並在這裡留下原因）。

## 1. `cmds/play4.py` 無法 import：缺少 `websockets`

- 位置：`cmds/music_bot/play4/player.py:9` `import websockets`
- 現況：`websockets` 不在 `pyproject.toml`、也不在 `uv.lock`，venv 內也沒有安裝，
  所以 `import cmds.play4` 直接 `ModuleNotFoundError`；`newbot2.py` 的 `load()` 會把它
  當成載入失敗（只記 warning），`/play` 等音樂指令實際上不會註冊。
- 影響測試：`tests/test_cmds/test_music/test_play4.py` 整個檔案 skip。
- 可能修法（未執行）：`uv add websockets`，或把 `websockets` 加進 `pyproject.toml` 的依賴。

## 2. 裸跑 `pytest` 會把 `cmds/data.json/data_test.py` 當成測試收集

- 位置：`cmds/data.json/data_test.py:13`
- 現況：檔名符合 pytest 預設的 `*_test.py`，被收集後在 import 時開檔
  `./cmds/cmds/data.json/skyblock_bazaar_item_tracker.txt`（路徑多了一層）而
  `FileNotFoundError`，導致整個 `pytest` collection 中斷。
- 目前處置：新增根目錄 `pytest.ini`，設定 `testpaths = tests` 與
  `python_files = test_*.py`，沒有動 `cmds/`。

## 3. `cmds/world_chat.py`：世界頻道訊息轉發實際不會發生

- 位置：`cmds/world_chat.py:57-59`
- 現況：`translations.get('components', {}).get('embed_world_chat')` 拿到的是 **list**
  （locale JSON 原始值），卻直接丟給 `load_translated()`，而它會呼叫
  `item.encode('utf-8')` → `AttributeError`；這個例外被同一個 `try` 的
  `except Exception` 吞掉，只印出訊息，因此**其他頻道收不到同步訊息**。
  `History` 仍在迴圈之後寫入，所以歷史紀錄看起來正常。
- 影響測試：`test_world_chat.py` 的兩個轉發測試以 `xfail(strict=True)` 標記，
  另外有一個測試驗證「History 仍會寫入」。

## 4. `cmds/bot_info_help.py`：`/help` 的指令自動完成（未指定 cog 時）會拋錯

- 位置：`cmds/bot_info_help.py:93-95`
- 現況：沒有 `cog_name` 時 `cmds = bot.commands`，而 `bot.commands` 是 `dict`，
  下一行 `[c.name for c in cmds]` 迭代到的是 key（`str`）→ `AttributeError`。
  指定 `cog_name` 時 `cog.get_commands()` 是 list，正常。
- 影響測試：`test_bot_info_help.py` 的兩個「未指定 cog」案例以 `xfail(strict=True)` 標記。

## 5. `zh-TW` locale 缺少部分 key（會直接顯示 key 名稱）

- `send_petpet_no_image`（`cmds/main.py` 的 `/petpet` 沒帶圖片時使用）
- `send_report_trace_not_exist`（`cmds/suggest_report.py` 的 `/report_trace` 查不到時使用）
- 影響：這些情況使用者會看到原始 key 字串；測試只斷言「有送出訊息」，不依賴譯文。

## 6. `cmds/qrcode.py`：Windows 上 `/qrcode_generator` 會 `PermissionError`

- 位置：`cmds/qrcode.py:48-49`
- 現況：`discord.File(path)` 會先開啟檔案，接著 `os.remove(path)`；Windows 上被開啟的
  檔案無法刪除（`WinError 32`），於是丟出 `PermissionError`。Linux 部署環境沒有這個問題。
- 影響測試：`test_qrcode.py` 以假的 `discord.File` 驗證流程（含刪除暫存檔），
  沒有修改 `cmds/qrcode.py`。
