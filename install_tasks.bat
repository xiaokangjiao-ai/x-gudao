@echo off
chcp 65001 > nul
echo ===================================
echo 股道奇货 - 定时任务安装脚本
echo ===================================
echo.

echo 创建任务: 股道奇货-美股更新 (每天 05:00 北京时间)
schtasks /Create /TN "股道奇货-美股更新" /TR "C:\Users\Administrator\x-gudao\gh-pages\update_us.bat" /SC DAILY /ST 05:00 /F

echo.
echo 创建任务: 股道奇货-A股更新 (每天 15:30 北京时间)
schtasks /Create /TN "股道奇货-A股更新" /TR "C:\Users\Administrator\x-gudao\gh-pages\update_ashare.bat" /SC DAILY /ST 15:30 /F

echo.
echo ===================================
echo 定时任务创建完成！
echo.
echo 任务列表:
schtasks /Query /TN "股道奇货-美股更新" /FO LIST
echo.
schtasks /Query /TN "股道奇货-A股更新" /FO LIST

echo.
echo ===================================
echo 手动运行测试:
echo   schtasks /Run /TN "股道奇货-美股更新"
echo   schtasks /Run /TN "股道奇货-A股更新"
echo ===================================
pause
