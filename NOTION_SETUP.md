# Notion 博客同步配置指南

要实现 Notion 到 Hugo 博客的自动同步，您需要进行以下配置：

## 1. 准备 Notion

1.  **创建 Integration (获取 Token)**:
    *   访问 [Notion My Integrations](https://www.notion.so/my-integrations)。
    *   点击 "New integration"。
    *   Name: `Blog Sync` (或任意名称)。
    *   Associated workspace: 选择您的工作区。
    *   Type: Internal integration。
    *   提交后，复制 **Internal Integration Secret** (即 `NOTION_TOKEN`)。

2.  **准备 Database**:
    *   在 Notion 中创建一个用于写博客的 Database（如果还没有）。
    *   确保包含以下属性（列）：
        *   `Name` (Title 类型): 文章标题
        *   `Status` (Status 类型): 必须包含 `Published` 选项，脚本只同步状态为 `Published` 的文章。
        *   `Date` (Date 类型): 发布日期
        *   `Tags` (Multi-select 类型): 标签
        *   `Slug` (Text 类型, 可选): 自定义 URL 路径
    *   **关键步骤**：在 Database 页面右上角点击 `...` -> `Connections` -> `Add connections` -> 选择刚才创建的 `Blog Sync`。这一步授权脚本访问该 Database。

3.  **获取 Database ID**:
    *   在浏览器中打开该 Database 页面。
    *   URL 格式通常为：`https://www.notion.so/myworkspace/{database_id}?v={view_id}`
    *   复制 `{database_id}` 部分（32个字符的字符串）。

## 2. 本地使用 (Skill)

您可以使用我为您创建的 `notion-sync` Skill 在本地手动同步。

1.  **配置环境变量**：
    在终端中运行：
    ```bash
    export NOTION_TOKEN="您的_token_粘贴在这里"
    export NOTION_DATABASE_ID="您的_database_id_粘贴在这里"
    ```

2.  **运行同步**：
    告诉我会话助手：“同步 Notion” 或运行：
    ```bash
    pip3 install -r tools/notion_sync/requirements.txt
    python3 tools/notion_sync/sync.py
    ```

## 3. GitHub Actions 自动同步

要让 GitHub 每天自动同步，或手动触发同步：

1.  打开您的 GitHub 仓库页面。
2.  进入 `Settings` -> `Secrets and variables` -> `Actions`。
3.  点击 `New repository secret`，添加两个密钥：
    *   Name: `NOTION_TOKEN`, Value: (您的 Token)
    *   Name: `NOTION_DATABASE_ID`, Value: (您的 Database ID)

配置完成后，GitHub Actions 会在每天 UTC 0点（北京时间早上8点）自动运行同步脚本，并将新文章推送到仓库。
