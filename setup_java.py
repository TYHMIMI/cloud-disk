#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java 环境自动配置脚本 —— setup_java.py
========================================
功能:
    扫描所有可移动硬盘(U盘/移动硬盘), 找到根目录带验证文件的那个,
    自动配置 JAVA_HOME 和 PATH.

目录约定 (移动硬盘根目录):
    <盘>:\
    ├── .java_marker          ← 验证文件 (空文件即可, 手动创建)
    └── JAVA\
        └── bin\
            └── java.exe     ← JDK 或 JRE 的 java.exe

用法:
    python setup_java.py              # 运行后暂停, 适合手动双击
    python setup_java.py --silent     # 静默模式, 适合开机自启
"""

import argparse
import ctypes
import os
import sys
import subprocess
import time

# Windows only
if not sys.platform.startswith("win"):
    print("[错误] 本脚本仅支持 Windows 系统")
    sys.exit(1)

import winreg


# ------------------------------------------------------------------
# 配置项
# ------------------------------------------------------------------
MARKER_FILE = ".java_marker"          # 验证文件名
JAVA_DIR_NAME = "JAVA"                # Java 目录名 (根目录下)
SIGNATURE = "JAVA_AUTO_SETUP_V1"      # 验证文件签名 (可选, 第一行)


# ------------------------------------------------------------------
# 枚举可移动硬盘
# ------------------------------------------------------------------
def list_removable_drives():
    """返回所有可移动硬盘盘符列表, 例如 ['E:', 'F:']"""
    drives = []
    kernel32 = ctypes.windll.kernel32
    # GetLogicalDrives 返回一个位图, bit N 代表盘符 A+(N-1)
    bitmask = kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            drive = f"{chr(ord('A') + i)}:\\"
            # DRIVE_REMOVABLE = 2
            if kernel32.GetDriveTypeW(drive) == 2:
                drives.append(drive)
    return drives


# ------------------------------------------------------------------
# 在移动硬盘中查找 Java 环境
# ------------------------------------------------------------------
def find_java():
    """
    扫描所有可移动硬盘, 找到同时满足以下条件的第一个盘:
      1) 根目录存在 .java_marker
      2) <盘>:\\JAVA\\bin\\java.exe 存在
    返回 (盘符, JAVA_HOME完整路径) 或 (None, None)
    """
    drives = list_removable_drives()
    if not drives:
        print("[扫描] 未检测到任何可移动硬盘")
        return None, None

    print(f"[扫描] 检测到 {len(drives)} 个可移动硬盘: {', '.join(drives)}")

    for drive in drives:
        marker_path = os.path.join(drive, MARKER_FILE)
        java_exe = os.path.join(drive, JAVA_DIR_NAME, "bin", "java.exe")

        print(f"  检查 {drive} ...")

        # 条件1: 验证文件存在
        if not os.path.isfile(marker_path):
            print(f"    ✗ 缺少 {MARKER_FILE}")
            continue

        # 条件2: 验证签名 (可选, 文件第一行)
        try:
            with open(marker_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
            if first_line and first_line != SIGNATURE:
                print(f"    ✗ 验证文件签名不匹配: {first_line}")
                continue
        except OSError as e:
            print(f"    ✗ 验证文件读取失败: {e}")
            continue

        # 条件3: java.exe 存在
        if not os.path.isfile(java_exe):
            print(f"    ✗ 缺少 {java_exe}")
            continue

        # 全部通过
        java_home = os.path.join(drive, JAVA_DIR_NAME)
        print(f"    ✓ 匹配成功！")
        return drive, java_home

    print("[扫描] 没有找到有效的 Java 环境")
    return None, None


# ------------------------------------------------------------------
# Windows 环境变量操作 (用户级, 持久化)
# ------------------------------------------------------------------
HKCU = winreg.HKEY_CURRENT_USER
ENV_KEY = r"Environment"


def get_user_env(name):
    r"""读取 HKCU\Environment 下的某个值"""
    try:
        with winreg.OpenKey(HKCU, ENV_KEY, 0, winreg.KEY_READ) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None
    except OSError:
        return None


def set_user_env(name, value):
    r"""写入 HKCU\Environment 并广播 WM_SETTINGCHANGE"""
    with winreg.CreateKey(HKCU, ENV_KEY) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    # 通知系统环境变量已变更
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    SMTO_ABORTIFHUNG = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
        SMTO_ABORTIFHUNG, 5000, None
    )


def set_java_env(java_home):
    """设置 JAVA_HOME 并将 bin 追加到 PATH (去重)"""
    java_bin = os.path.join(java_home, "bin")

    # --- JAVA_HOME ---
    print(f"\n[配置] JAVA_HOME = {java_home}")
    set_user_env("JAVA_HOME", java_home)
    # 当前会话也立即生效
    os.environ["JAVA_HOME"] = java_home

    # --- PATH 去重追加 ---
    current_path = get_user_env("Path") or ""
    path_entries = [p.strip() for p in current_path.split(";") if p.strip()]

    already = any(
        os.path.normcase(p) == os.path.normcase(java_bin)
        or os.path.normcase(p) == os.path.normcase(f"%JAVA_HOME%\\bin")
        for p in path_entries
    )

    if not already:
        new_path = ";".join(path_entries + [java_bin])
        print(f"[配置] 追加到 PATH: {java_bin}")
        set_user_env("Path", new_path)
    else:
        print(f"[配置] PATH 已包含 {java_bin}, 跳过")

    # 当前会话立即生效
    os.environ["PATH"] = java_bin + os.pathsep + os.environ.get("PATH", "")


# ------------------------------------------------------------------
# 验证 Java 是否可用
# ------------------------------------------------------------------
def verify_java(java_home):
    java_exe = os.path.join(java_home, "bin", "java.exe")
    if not os.path.isfile(java_exe):
        print(f"[验证] ✗ {java_exe} 不存在")
        return False

    try:
        result = subprocess.run(
            [java_exe, "-version"],
            capture_output=True, text=True, timeout=10
        )
        version_line = (result.stderr or result.stdout).strip().splitlines()
        if result.returncode == 0:
            print("[验证] ✓ Java 运行正常")
            if version_line:
                print(f"       {version_line[0]}")
            return True
        else:
            print(f"[验证] ✗ java -version 返回错误码 {result.returncode}")
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[验证] ✗ java.exe 执行失败: {e}")
        return False


# ------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Java 环境自动配置")
    parser.add_argument("--silent", action="store_true",
                        help="静默模式 (不等待回车, 适合开机自启)")
    args = parser.parse_args()

    print("=" * 50)
    print("  Java 环境自动配置  v1.0  (纯标准库, Windows)")
    print("=" * 50)

    # 1. 查找 Java
    drive, java_home = find_java()
    if not java_home:
        print("\n[结果] 配置失败 — 没有找到有效的 Java 环境")
        if not args.silent:
            input("按回车键退出...")
        sys.exit(1)

    # 2. 验证 java.exe
    print()
    ok = verify_java(java_home)

    # 3. 设置环境变量
    set_java_env(java_home)

    # 4. 完成
    print("\n" + "=" * 50)
    print("  配置完成!")
    print("=" * 50)
    print(f"  JAVA_HOME = {java_home}")
    print(f"  java.exe  = {os.path.join(java_home, 'bin', 'java.exe')}")
    if not ok:
        print("  (警告: java.exe 执行有异常, 请检查 JDK 文件完整性)")

    # 5. 如果当前系统能直接跑 java 也再试一下
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
        v = (r.stderr or r.stdout).strip().splitlines()
        if v:
            print(f"\n  当前终端 java: {v[0]}")
    except OSError:
        pass

    if not args.silent:
        input("\n按回车键退出...")


if __name__ == "__main__":
    main()
