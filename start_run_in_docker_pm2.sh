#!/bin/bash
pm2 start newbot2.py --name "DiscordBot" --interpreter python3 \
  --log logs/combined.log \
  --output logs/output.log \
  --error logs/error.log \
  --merge-logs \
  --log-date-format "YYYY-MM-DD HH:mm:ss" \
