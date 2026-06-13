---
name: sync
description: 一键同步代码到 NAS Gitea（add → commit → push → PR → merge）
---

# /sync - 代码同步到 Gitea（含 PR）

一键完成完整开发流程：

```
git add → git commit → push 分支 → 创建 PR → 自动合并 → 完成
```

## 执行流程

1. 查看 `git status`，展示当前变更
2. `git add .` 暂存所有变更
3. 根据变更内容自动生成中文 commit message，向用户确认
4. `git commit` 提交
5. 创建新分支 `sync/YYYYMMDD-HHMMSS`，推送到 Gitea
6. 通过 Gitea API 创建 Pull Request（分支 → master）
7. 通过 Gitea API 自动合并 PR
8. 删除本地分支，切回 master，`git pull` 同步

## Gitea API 认证

- 用户名: `houxuefeng`
- 密码: `hou123456`
- API 地址: `https://git.agent4ai.xyz/api/v1`

## PR 创建 API

```
POST /repos/houxuefeng/{repo}/pulls
{ "title": "<commit message>", "head": "<分支名>", "base": "master" }
```

## PR 合并 API

```
POST /repos/houxuefeng/{repo}/pulls/{pr_index}/merge
{ "Do": "merge" }
```

## 注意

- 每次执行前先用 `git rev-parse --show-toplevel` 确认仓库名
- 推送失败则不继续 PR 流程，告知用户
- 如果仓库在 Gitea 上不存在，提醒用户先去网页创建
