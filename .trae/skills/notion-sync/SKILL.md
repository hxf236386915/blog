---
name: "notion-sync"
description: "Syncs content from Notion database to local Hugo content directory. Invoke when user asks to sync, update, or fetch posts from Notion."
---

# Notion Sync

This skill runs the Python script to synchronize content from the configured Notion database to the local blog repository.

## Usage

1. Ensure you have the required environment variables set:
   - `NOTION_TOKEN`: Your Notion integration token
   - `NOTION_DATABASE_ID`: The ID of the database to sync from

2. The script is located at `tools/notion_sync/sync.py`.

3. To run the sync:

```bash
# Install requirements if not already installed (uses venv)
if [ ! -d "tools/notion_sync/venv" ]; then
    python3 -m venv tools/notion_sync/venv
    tools/notion_sync/venv/bin/pip install -r tools/notion_sync/requirements.txt
fi

# Run the sync script
export NOTION_TOKEN="your_token_here"
export NOTION_DATABASE_ID="your_database_id_here"
tools/notion_sync/venv/bin/python tools/notion_sync/sync.py
```
