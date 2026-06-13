---
name: sync
description: 同步代码到 Gitea 并创建 PR 供审查
---

# /sync - 代码同步到 Gitea（创建 PR，你来合并）

```
git add → commit → push 分支 → 创建 PR → 👈 你审查后手动合并
```

## 执行流程

1. `git status` — 展示变更文件列表，统计新增/修改/删除
2. `git diff` — 查看具体改动内容，用于生成 PR 说明
3. `git add .` — 暂存所有变更
4. 根据 diff 内容自动生成中文 commit message，**向用户确认**
5. `git checkout -b sync/YYYYMMDD-HHMMSS` — 创建功能分支
6. `git commit` — 提交
7. `git push` — 推送到 Gitea
8. 通过 Gitea API 创建 Pull Request
9. 用浏览器打开 PR 页面，让用户审查后手动合并

## PR 描述模板

创建 PR 时必须包含以下内容：

```markdown
## 📝 变更概述
<一句话说明这次改了什么，解决什么问题>

## 🔧 功能变更
- <变更点1>
- <变更点2>

## 📁 文件变更
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| path/to/file | 新增/修改/删除 | <简要说明> |

## 🧪 如何测试
1. <测试步骤1>
2. <测试步骤2>
3. <预期结果>

## ⚠️ 注意事项
- <需要注意的风险点、依赖变更、配置变更等>
```

## PR 生成规则

- **变更概述**：从 commit message 推导
- **功能变更**：从 diff 中提取关键改动
- **文件变更**：列出所有变更文件，标注 新增/修改/删除 和行数
- **如何测试**：根据变更类型推断测试方法（前端→页面测试、API→curl、脚本→命令行）
- **注意事项**：检查是否有新增依赖、配置变更、破坏性改动

## Gitea API 认证

- 用户名: `houxuefeng`
- 密码: `hou123456`
- API 地址: `https://git.agent4ai.xyz/api/v1`

## PR 创建 API

```
POST /repos/houxuefeng/{repo}/pulls
{
  "title": "<commit message>",
  "head": "<分支名>",
  "base": "master",
  "body": "<按模板生成的 PR 描述>"
}
```

## 注意

- 每次执行前用 `git rev-parse --show-toplevel` 确认仓库名和当前分支
- **先在分支上 commit，再 push 分支**，不要在 master 上 commit
- 仓库不存在于 Gitea 时，提醒用户先去网页创建
