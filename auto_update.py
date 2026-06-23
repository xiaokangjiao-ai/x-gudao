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

# 设置路径
ROOT = Path(__file__).parent.parent.resolve()
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

def update_all_data():
    """更新所有标的的数据"""
    print(f"\n{'='*60}")
    print(f"开始更新数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 导入生成脚本
    try:
        from generate_static import main as generate_main
        import argparse
        
        # 模拟命令行参数
        sys.argv = ['generate_static.py']
        generate_main()
        
        print(f"\n✅ 数据更新完成！")
        return True
    except Exception as e:
        print(f"\n❌ 数据更新失败: {e}")
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
        os.system(f'git commit -m "{commit_msg}"')
        
        # 推送
        print("\n[PUSH] 推送到 GitHub...")
        ret = os.system('git push origin gh-pages')
        
        if ret == 0:
            print("✅ 推送成功！")
            return True
        else:
            print("❌ 推送失败")
            return False
    except Exception as e:
        print(f"❌ Git 操作失败: {e}")
        return False


if __name__ == '__main__':
    print("="*60)
    print("股道奇货 - 定时数据更新脚本")
    print("="*60)
    
    # 更新数据
    if update_all_data():
        # 推送到GitHub
        git_commit_push()
    else:
        print("\n⚠️ 数据更新失败，不执行推送")
        sys.exit(1)
