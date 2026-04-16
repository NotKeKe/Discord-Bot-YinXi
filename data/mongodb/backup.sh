#!/bin/sh

BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_BACKUP="${BACKUP_DIR}/backup_${TIMESTAMP}"

echo "[$(date)] 🔄 開始備份到 ${NEW_BACKUP}..."

mongodump \
  --host=mongodb \
  --username="${MONGO_USER}" \
  --password="${MONGO_PASSWORD}" \
  --authenticationDatabase=admin \
  --out="${NEW_BACKUP}"

if [ $? -eq 0 ]; then
  echo "[$(date)] ✅ 備份完成"

  # --- 刪除舊備份邏輯 ---
  echo "[$(date)] 🧹 正在清理舊備份 (僅保留最近 10 個)..."
  
  # 1. 切換到備份目錄
  # 2. 按時間順序（由舊到新）列出資料夾
  # 3. 找出除了最後（最新）10 個以外的所有資料夾
  # 4. 刪除它們
  ls -1dt ${BACKUP_DIR}/backup_* 2>/dev/null | tail -n +11 | xargs rm -rf

  echo "[$(date)] ✨ 清理完成"
else
  echo "[$(date)] ❌ 備份失敗"
  exit 1
fi