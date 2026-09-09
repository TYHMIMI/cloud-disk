@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  验证文件生成器 —— gen_verify.bat
rem  用法:
rem    1) 插入U盘/移动硬盘
rem    2) 双击运行本脚本，按提示选择目标盘
rem    3) 脚本会在该盘根目录生成 java_verify.dat
rem    4) 之后把 JAVA 文件夹（含 bin\java.exe）也放到该盘根目录
rem ============================================================

echo.
echo ================================================
echo   Java 验证文件生成器  v1.0
echo ================================================
echo.

rem ---------- 枚举所有可移动硬盘 ----------
set "count=0"
for /f "skip=1 tokens=1,2 delims==" %%A in ('wmic logicaldisk where "drivetype=2" get deviceid^,volumename /format:list 2^>nul') do (
    if "%%A"=="DeviceID" (
        set /a count+=1
        set "dev!count!=%%B"
        set "dev!count!=!dev!count!:~0,-1!"
    )
)

if %count%==0 (
    echo [错误] 没有检测到任何可移动硬盘！
    echo 请先插入U盘或移动硬盘后重试。
    pause
    exit /b 1
)

echo 检测到 %count% 个可移动硬盘:
for /l %%i in (1,1,%count%) do echo   [%%i] !dev%%i!
echo.

rem ---------- 让用户选择 ----------
set /p "choice=请选择目标磁盘编号 (1-%count%): "

if "%choice%"=="" (
    echo [错误] 未输入。
    pause
    exit /b 1
)

set "target=!dev%choice%!"

if not exist "%target%\" (
    echo [错误] 目标盘 %target% 不存在。
    pause
    exit /b 1
)

rem ---------- 生成验证文件 ----------
set "verify_file=%target%\java_verify.dat"
(
    echo JAVA_SETUP_OK_V1
    echo Created: %date% %time%
) > "%verify_file%"

echo.
echo [成功] 验证文件已生成: %verify_file%

rem ---------- 提示用户放入JDK ----------
if exist "%target%\JAVA\bin\java.exe" (
    echo [OK] 检测到 %target%\JAVA\bin\java.exe，Java 目录就绪！
) else (
    echo.
    echo [注意] 未检测到 %target%\JAVA\bin\java.exe
    echo        请把你的 JDK/JRE 文件夹重命名为 JAVA 并放到 %target%\ 根目录下。
    echo        最终结构应为: %target%\JAVA\bin\java.exe
)

echo.
pause
endlocal
exit /b 0
