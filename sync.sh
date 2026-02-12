#!/bin/bash

# 加载环境变量（如果存在）
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# 检查必要的环境变量
if [ -z "$NOTION_TOKEN" ] || [ -z "$NOTION_DATABASE_ID" ]; then
  echo "❌ 错误: 未设置 NOTION_TOKEN 或 NOTION_DATABASE_ID。"
  echo "请先导出这些变量，或者将它们写入 .env 文件。"
  exit 1
fi

echo "🚀 开始同步 Notion 文章..."

# 检查虚拟环境是否存在，不存在则创建
if [ ! -d "tools/notion_sync/venv" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv tools/notion_sync/venv
    tools/notion_sync/venv/bin/pip install -r tools/notion_sync/requirements.txt
fi

# 运行同步脚本
tools/notion_sync/venv/bin/python tools/notion_sync/sync.py

echo "✅ 同步完成！请检查 content/blog 目录。"
