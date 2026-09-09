@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  Java 环境自动配置脚本 —— setup_java.bat
rem  功能: 自动搜索所有可移动硬盘，找到带验证文件的那个，
rem        从中加载 JDK/JRE 并配置 JAVA_HOME + PATH
rem  用法: 双击运行即可（建议放到 Windows 启动文件夹实现开机自动配置）
rem ============================================================

echo.
echo ================================================
echo   Java 环境自动配置  v1.0
echo ================================================
echo.

rem ---------- 枚举所有可移动硬盘 ----------
set "java_drive="

for /f "skip=1 tokens=1,2 delims==" %%A in ('wmic logicaldisk where "drivetype=2" get deviceid^,volumename /format:list 2^>nul') do (
    if "%%A"=="DeviceID" (
        set "drive=%%B"
        set "drive=!drive:~0,-1!"

        echo  扫描 !drive! ...

        rem ---------- 检查验证文件 ----------
        if exist "!drive!\java_verify.dat" (
            rem 读取第一行验证签名
            set /p "verify_line=" < "!drive!\java_verify.dat"
            if "!verify_line!"=="JAVA_SETUP_OK_V1" (
                rem 验证通过，检查 java.exe
                if exist "!drive!\JAVA\bin\java.exe" (
                    set "java_drive=!drive!"
                    echo  [匹配] 找到验证文件且 java.exe 存在 !
                    goto :found
                ) else (
                    echo  [跳过] !drive!\java_verify.dat 存在但没有 !drive!\JAVA\bin\java.exe
                )
            ) else (
                echo  [跳过] !drive!\java_verify.dat 签名不匹配
            )
        )
    )
)

rem ---------- 没找到 ----------
echo.
echo [结果] 没有在任何可移动硬盘上找到有效的 Java 环境。
echo        请确认:
echo          1) 插入了含 java_verify.dat 的移动硬盘
echo          2) 硬盘根目录下有 JAVA\bin\java.exe
echo.
pause
exit /b 1

rem ============================================================
rem  找到 Java 了 —— 开始配置
rem ============================================================
:found
set "JAVA_HOME=%java_drive%\JAVA"

echo.
echo  JAVA_HOME  = %JAVA_HOME%
echo  java.exe   = %JAVA_HOME%\bin\java.exe
echo.

rem ---------- 验证 Java 能正常运行 ----------
"%JAVA_HOME%\bin\java.exe" -version >nul 2>&1
if errorlevel 1 (
    echo [警告] java.exe 执行失败，可能 JDK 文件不完整。
    echo        但仍会继续设置环境变量。
) else (
    echo [OK] Java 运行正常
    "%JAVA_HOME%\bin\java.exe" -version 2>&1 | findstr /i "version"
)

rem ---------- 持久化设置 JAVA_HOME (用户级) ----------
echo.
echo 正在写入环境变量...
setx JAVA_HOME "%JAVA_HOME%" >nul

rem ---------- 持久化设置 PATH ----------
rem 先读取当前用户 PATH，追加 %JAVA_HOME%\bin（避免重复）
set "user_path="
for /f "usebackq delims=" %%P in (`reg query "HKCU\Environment" /v Path 2^>nul ^| findstr /i "Path"`) do (
    for /f "tokens=3*" %%Q in ("%%P") do set "user_path=%%Q"
)

if not defined user_path (
    set "user_path="
)

rem 检查是否已包含 %JAVA_HOME%\bin
echo "!user_path!" | findstr /i /c:"%JAVA_HOME%\bin" >nul 2>&1
if errorlevel 1 (
    rem 没包含，追加
    if "!user_path!"=="" (
        set "new_path=%JAVA_HOME%\bin"
    ) else (
        set "new_path=!user_path!;%JAVA_HOME%\bin"
    )
    setx Path "!new_path!" >nul
    echo  [OK] 已将 %JAVA_HOME%\bin 追加到用户 PATH
) else (
    echo  [OK] 用户 PATH 已包含 %JAVA_HOME%\bin，无需重复添加
)

rem ---------- 当前会话立即生效 ----------
set "JAVA_HOME=%JAVA_HOME%"
set "PATH=%JAVA_HOME%\bin;%PATH%"

rem ---------- 再次验证 ----------
echo.
echo ================================================
echo  配置完成！验证结果:
echo ================================================
where java 2>nul
java -version 2>&1 | findstr /i "version"
echo.

rem 如果不是开机自启模式，暂停让用户看到结果
if not "%~1"=="--silent" (
    pause
)
endlocal
exit /b 0
