# [任務目標]
你是一位資深的 Python discord.py 機器人國際化 (i18n) 專家。你的任務是**審計、修正並完成** `cmds/` 目錄下所有 `.py` 程式檔的 i18n 重構。

**重要背景**：此專案的 i18n 實作存在不一致與錯誤。部分鍵名 (key) 不符合規範，導致調用混亂。你的任務是將所有 i18n 相關的程式碼統一到正確的架構下。你的審查範圍必須包含：
1.  指令裝飾器 (`@commands.hybrid_command`, `@app_commands.describe`)。
2.  指令內部的翻譯調用 (`interaction.translate`)。

# [核心流程]
對於 `cmds/` 目錄下的每一個 Python 檔案，你的工作流程如下：

1.  **審查與修正 (Review & Correct):**
    *   檢查檔案中每一個 `locale_str("...")` 和 `interaction.translate("...")` 的調用。
    *   判斷它們使用的 key 是否符合你從學習階段推導出的命名規範。
    *   如果不符合，你必須 **同時修正** Python 檔案中的調用和 `core/locales/zh-TW.json` 中的對應鍵名。
    *   **目前已知錯誤模式**:
        *   **不規範的扁平命名**: 類似 `component_channel_history_txt_parts` 這樣的 key 沒有遵循應有的結構。
        *   **錯誤的巢狀結構表示**: 類似 `embed_giveaway_winners_total_field` 這樣的扁平 key 是錯誤的。它應該被重構為巢狀的 JSON 物件，其結構應參考 `zh-TW.json` 中 `embed_help_main` 的實現方式。

2.  **新增與完成 (Add & Complete):**
    *   找出檔案中任何尚未被 i18n 化的硬編碼字串（尤其是在指令裝飾器中）。
    *   為這些字串生成符合規範的 key，修改 Python 檔案，並將新的鍵值對添加到 `zh-TW.json`。

---

# [學習階段：推導規則與標準]
在開始修改前，你必須先**自行推導出官方的命名規範**。這是你後續所有審查、修正與新增工作的唯一標準。

1.  **推導命名規範**:
    *   仔細研究 `core/translator.py`，特別是 `i18n` class 內的註解和實現，理解其設計哲學。
        *   查看 `i18n` class 內部的 `example`，並特別注意註解的部分，那是他的命名方式。
        *   查看 `load_translated` function ，了結它的用途。
    *   仔細研究 `core/locales/zh-TW.json` 中上半部現有的、結構良好的鍵值對，逆向工程出 key 的標準命名結構（例如，檔名、指令名、元素類型是如何組合的）。

2.  **參考實現**:
    *   將 `cmds/qrcode_generator.py` 和 `cmds/translator.py` 視為**黃金標準 (Gold Standard)**。在你完成修改後，所有其他指令檔的 i18n 實現都應該與這兩個檔案的風格和結構保持一致。
        *   例如: 會使用'''1i8n'''SOME CODE HERE ''''''將翻譯部分包起來。

---

# [執行階段：具體修正步驟]
當你處理一個檔案時（例如 `cmds/ping.py`），請嚴格遵循以下步驟：

1.  **全面掃描**: 掃描檔案中所有的指令裝飾器和函式內部的 `interaction.translate` 調用。

2.  **識別問題**:
    *   **問題A (裝飾器鍵名錯誤)**: 發現 `name=locale_str("ping_command_name")`。
    *   **問題B (裝飾器尚未i18n)**: 發現 `description="Shows bot latency"`。
    *   **問題C (內部調用鍵名錯誤)**: 發現 `interaction.translate("ping_response")`。

3.  **生成修正方案**:
    *   根據你在學習階段推導出的**命名規範**，為上述所有問題生成正確的 key。
    *   對於**問題A和C**:
        *   準備對 Python 檔的修改，將錯誤的 key 替換為你生成的正確 key。
        *   準備對 `zh-TW.json` 的修改，將錯誤的 key 替換為正確的 key。
    *   對於**問題B**:
        *   準備對 Python 檔的修改，將硬編碼字串替換為 `locale_str(正確的key)`。
        *   準備將新的鍵值對新增到 `zh-TW.json`。

4.  **準備輸出**:
    *   **第一部分 (Python 檔案)**: 使用適當工具，編寫完整的、**已完全修正**的 Python 檔案程式碼。所有 i18n 調用都必須使用**正確**的鍵名。
    *   **第二部分 (JSON 更新)**: 使用適當工具，編寫**已修正的 JSON 程式碼**。這個區塊應該包含所有**新增**和**修正後**的鍵值對。最終應存在於 `zh-TW.json` 中。並且確保語言為繁體中文，並 **僅編寫至 `zh-TW.json` 檔案** 中，而非其他 JSON 檔。

---

# [嚴格限制]
1.  你**必須修正** `zh-TW.json` 中所有**命名不規範的鍵 (key)**，使其符合你推導出的標準。
2.  當你修正一個鍵名時，請確保其對應的**值 (value) 保持不變**。
3.  **絕對禁止**修改 Python 檔案中除了 `import` 和 i18n 相關調用以外的任何程式碼邏輯。