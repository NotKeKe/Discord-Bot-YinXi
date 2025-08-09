#!/bin/sh

echo "[$(date)] 🔄 開始備份..."

mongodump \
  --host=mongodb \
  --username="${MONGO_USER}" \
  --password="${MONGO_PASSWORD}" \
  --authenticationDatabase=admin \
  --out=/backup/backup_$(date +%Y%m%d_%H%M%S)

if [ $? -eq 0 ]; then
  echo "[$(date)] ✅ 備份完成"
else
  echo "[$(date)] ❌ 備份失敗"
  exit 1
fi
