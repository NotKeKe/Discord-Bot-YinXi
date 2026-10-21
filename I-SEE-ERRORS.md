# I-SEE-ERRORS

測試與整理 `cmds/` 指令時發現、但**尚未處理**的問題。
（已修正、已被設定排除或其實不是 bug 的項目會直接從本檔移除。）

## 1. `cmds/qrcode.py`：Windows 上 `/qrcode_generator` 會 `PermissionError`

- 位置：`cmds/qrcode.py:48-49`
- 現況：`discord.File(path)` 會先開啟檔案，接著 `os.remove(path)`；Windows 不允許刪除
  仍被開啟的檔案（`WinError 32`）→ `PermissionError`。Linux 部署環境沒有這個問題。
- 影響測試：`test_qrcode.py` 以假的 `discord.File` 驗證流程（含刪除暫存檔），
  沒有修改 `cmds/qrcode.py`。
