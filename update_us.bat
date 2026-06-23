@echo off
chcp 65001 > nul
echo ===================================
echo 股道奇货 - 美股数据更新任务
echo 运行时间: %date% %time%
echo ===================================

cd /d C:\Users\Administrator\x-gudao\gh-pages

echo.
echo [1/3] 更新数据...
python src/generate_static.py --skip-fetch 2>&1 | findstr /V "SKIP-FETCH FALLBACK DB OK"

echo.
echo [2/3] 提交到Git...
git add -A
git commit -m "auto-update: US stocks %date:~0,10% %time:~0,5%"

echo.
echo [3/3] 推送到GitHub...
git push origin gh-pages

echo.
echo ===================================
echo 更新完成！
echo ===================================
pause
