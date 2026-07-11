#!/usr/bin/env python3
"""
定时数据更新脚本
- 美股收盘后更新 (北京时间 05:00 / 美股 16:00 EST)
- A股收盘后更新 (北京时间 15:30 / A股 15:00 CST)
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import time

# 确保输出编码为 UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 设置路径（基于本脚本所在目录，自动检测正确的项目根目录）
SCRIPT_DIR = Path(__file__).parent.resolve()
# 如果 gh-pages/src 存在，说明脚本在 gh-pages/ 下；否则取上一级
if (SCRIPT_DIR / "src").exists():
    ROOT = SCRIPT_DIR
else:
    ROOT = SCRIPT_DIR.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def update_all_data():
    """更新所有标的的数据"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新数据")
    print(f"{'='*60}\n")

    # 导入生成脚本
    try:
        from generate_static import main as generate_main
        import argparse

        # 模拟命令行参数
        sys.argv = ['generate_static.py']
        generate_main()

        print(f"\n[OK] 数据更新完成!")

        # === 关键：把 _site/ 生成结果复制到 gh-pages 根目录（否则 gitignore 会忽略它们）===
        import shutil
        site_dir = ROOT / "_site"
        for item in site_dir.iterdir():
            dest = ROOT / item.name
            if dest.is_dir():
                shutil.rmtree(dest, ignore_errors=True)
            else:
                dest.unlink(missing_ok=True)
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"[OK] 已将 _site/ 内容同步到 gh-pages 根目录")
        return True
    except Exception as e:
        print(f"\n[ERROR] 数据更新失败: {e}")
        return False


def git_commit_push():
    """提交并推送更新"""
    try:
        os.chdir(ROOT)

        # 检查是否有变更
        result = os.popen('git status --porcelain').read().strip()
        if not result:
            print("\n[INFO] 没有数据变更，跳过提交")
            return True

        # 提交
        os.system('git add -A')
        commit_msg = f"auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ret_commit = os.system(f'git commit -m "{commit_msg}"')

        if ret_commit != 0:
            print("[ERROR] Git commit 失败")
            return False

        # 推送
        print("\n[PUSH] 推送到 GitHub gh-pages...")
        ret = os.system('git push origin gh-pages')

        if ret == 0:
            print("[OK] 推送成功!")
            return True
        else:
            print("[ERROR] 推送失败 (检查 git 认证或网络)")
            return False
    except Exception as e:
        print(f"[ERROR] Git 操作失败: {e}")
        return False


if __name__ == '__main__':
    print("="*60)
    print("股道奇货 - 定时数据更新脚本")
    print("="*60)

    # 更新数据
    if update_all_data():
        # 推送到 GitHub
        git_commit_push()
    else:
        print("\n[WARN] 数据更新失败，不执行推送")
        sys.exit(1)
