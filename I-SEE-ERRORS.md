# I-SEE-ERRORS

測試與整理 `cmds/` 指令時發現、但**尚未處理**的問題。
（已修正的項目會直接從本檔移除，例如 locale 缺 key、`play4` 缺 `websockets`。）

## 2. `cmds/bot_info_help.py`：`/help` 未指定 cog 時的指令自動完成會拋錯

- 位置：`cmds/bot_info_help.py:93-95`
- 現況：`cmds = bot.commands` 是 `dict`，下一行 `[c.name for c in cmds]` 迭代到的是 key（`str`）
  → `AttributeError`。指定 `cog_name` 時 `cog.get_commands()` 是 list，正常。
- 影響測試：`test_bot_info_help.py` 的兩個「未指定 cog」案例以 `xfail(strict=True)` 標記。

## 3. 裸跑 `pytest` 會收集 `cmds/data.json/data_test.py`

- 位置：`cmds/data.json/data_test.py:13`
- 現況：檔名符合 pytest 預設的 `*_test.py`，被收集後在 import 時開檔
  `./cmds/cmds/data.json/skyblock_bazaar_item_tracker.txt`（路徑多了一層）
  → `FileNotFoundError`，整個 collection 中斷。
- 目前處置：根目錄 `pytest.ini` 設 `testpaths = tests`、`python_files = test_*.py`，
  沒有動 `cmds/`。

## 4. `cmds/qrcode.py`：Windows 上 `/qrcode_generator` 會 `PermissionError`

- 位置：`cmds/qrcode.py:48-49`
- 現況：`discord.File(path)` 會先開啟檔案，接著 `os.remove(path)`；Windows 不允許刪除
  仍被開啟的檔案（`WinError 32`）→ `PermissionError`。Linux 部署環境沒有這個問題。
- 影響測試：`test_qrcode.py` 以假的 `discord.File` 驗證流程（含刪除暫存檔），
  沒有修改 `cmds/qrcode.py`。
