#!/usr/bin/env python3
"""
简化版数据更新脚本
- 美股：使用DB数据（skip-fetch）
- A股：实时获取（从新浪财经）
"""
import sys
import os
import json
from pathlib import Path
import time

ROOT = Path(__file__).parent.parent.resolve()
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

print(f"\n{'='*60}")
print(f"股道奇货 - 数据更新脚本")
print(f"{'='*60}\n")

# 1. 更新美股数据（使用DB）
print("[1/3] 更新美股数据（使用DB）...")
os.chdir(ROOT)
ret = os.system(f'{sys.executable} {SRC}/generate_static.py --skip-fetch')
if ret != 0:
    print("[ERROR] 美股数据更新失败")
    sys.exit(1)

print("\n✅ 美股数据更新完成\n")

# 2. 更新A股数据（如果需要重新获取）
print("[2/3] 更新A股数据...")
# A股数据已经在上面的步骤中获取了（generate_static.py 会读取 a_tickers）

print("\n✅ A股数据更新完成\n")

# 3. 提交并推送
print("[3/3] 提交并推送到GitHub...")

# 检查是否有变更
result = os.popen('git status --porcelain').read().strip()
if not result:
    print("[INFO] 没有数据变更，跳过提交")
    sys.exit(0)

# 提交
os.system('git add -A')
commit_msg = f"auto-update: {time.strftime('%Y-%m-%d %H:%M')}"
os.system(f'git commit -m "{commit_msg}"')

# 推送
print("\n[推送] 推送到 GitHub...")
ret = os.system('git push origin gh-pages')
if ret == 0:
    print("\n✅ 推送成功！")
    print(f"\n🌐 网站将在1-2分钟内更新：https://xiaokangjiao-ai.github.io/x-gudao/")
else:
    print("\n❌ 推送失败")
    sys.exit(1)
