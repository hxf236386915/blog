#!/usr/bin/env python3
"""
Git Sync 辅助脚本
用于自动检测项目中的 Git 仓库状态并生成同步报告
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path


def run_git_command(repo_path, *args):
    """在指定仓库中执行 git 命令"""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + list(args),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1


def get_repo_info(repo_path):
    """获取仓库基本信息"""
    info = {"path": repo_path, "name": os.path.basename(repo_path)}

    # 获取当前分支
    branch, _, _ = run_git_command(repo_path, "branch", "--show-current")
    info["branch"] = branch

    # 获取远程仓库
    remotes, _, _ = run_git_command(repo_path, "remote", "-v")
    info["remotes"] = remotes if remotes else "无"

    # 获取最新 commit
    log, _, _ = run_git_command(
        repo_path, "log", "--oneline", "-1", "--format=%h %s (%ar)"
    )
    info["last_commit"] = log

    # 获取未提交变更数量
    status, _, _ = run_git_command(repo_path, "status", "--porcelain")
    info["pending_changes"] = len(status.split("\n")) if status else 0

    return info


def find_git_repos(root_dir, max_depth=3):
    """递归查找所有 Git 仓库"""
    repos = []
    root = Path(root_dir)

    for path in root.rglob(".git"):
        if path.is_dir():
            depth = len(path.relative_to(root).parts) - 1
            if depth <= max_depth:
                repos.append(str(path.parent))

    return repos


def generate_sync_report(repos_info):
    """生成同步报告"""
    total = len(repos_info)
    dirty = sum(1 for r in repos_info if r["pending_changes"] > 0)
    clean = total - dirty

    report = []
    report.append("=" * 50)
    report.append(f"📊 Git 仓库同步报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 50)
    report.append(f"总仓库数: {total}  |  有变更: {dirty}  |  干净: {clean}")
    report.append("")

    for info in repos_info:
        status_icon = "🔴" if info["pending_changes"] > 0 else "🟢"
        report.append(f"{status_icon} {info['name']}")
        report.append(f"   分支: {info['branch']}")
        report.append(f"   最新: {info['last_commit']}")
        report.append(f"   待同步: {info['pending_changes']} 个变更")
        report.append("")

    return "\n".join(report)


def main():
    """主函数"""
    root_dir = os.path.expanduser("~/mac同步/cursor")
    print(f"🔍 扫描目录: {root_dir}\n")

    repos = find_git_repos(root_dir)
    print(f"找到 {len(repos)} 个 Git 仓库\n")

    repos_info = [get_repo_info(repo) for repo in repos]
    report = generate_sync_report(repos_info)
    print(report)

    # 保存报告
    report_file = os.path.expanduser("~/git-sync-report.txt")
    with open(report_file, "w") as f:
        f.write(report)
    print(f"📄 报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
