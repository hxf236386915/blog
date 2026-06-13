---
name: sync
description: 同步代码到 Gitea 并创建 PR 供审查
---

# /sync - 代码同步到 Gitea（创建 PR，你来合并）

```
git add → commit → push 分支 → 创建 PR → 👈 你审查后手动合并
```

## 执行流程

1. `git status` — 展示当前变更文件列表
2. `git add .` — 暂存所有变更
3. 根据变更内容自动生成中文 commit message，**向用户确认**
4. `git commit` — 提交
5. 创建新分支 `sync/YYYYMMDD-HHMMSS`，推送到 Gitea
6. 通过 Gitea API 创建 Pull Request：
   ```
   POST https://git.agent4ai.xyz/api/v1/repos/houxuefeng/{repo}/pulls
   认证: houxuefeng / hou123456
   请求体: { "title": "<commit message>", "head": "<分支名>", "base": "master" }
   ```
7. 用浏览器打开 PR 页面，让用户审查 diff
8. 用户自己决定：✅ 合并 或 ❌ 关闭

## 用户需要做的事情

- 确认 commit message
- 在浏览器中查看 PR 的 diff
- 点击「合并」按钮（或关闭 PR）

## 注意

- 每次执行前用 `git rev-parse --show-toplevel` 确认仓库名
- 仓库不存在于 Gitea 时，提醒用户先去网页创建
- PR 创建失败不阻塞，告知原因
