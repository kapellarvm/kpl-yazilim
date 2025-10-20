#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Terminal Çıktı Yardımcıları
Standart, okunabilir ve raporlanabilir terminal çıktı formatları
"""

from datetime import datetime
from typing import Optional


def _now() -> str:
    return datetime.now().strftime('%H:%M:%S')


def section(title: str, subtitle: Optional[str] = None) -> None:
    """Bölüm başlığı çıktısı üretir."""
    line = "=" * 60
    print(f"\n{line}")
    print(f"[{_now()}] {title}")
    if subtitle:
        print(f"[{_now()}] {subtitle}")
    print(line)


def status(context: str, message: str, level: str = "info") -> None:
    """Bağlamlı durum çıktısı. level: info|ok|warn|err|action|wait"""
    icons = {
        "info": "ℹ️ ",
        "ok": "✅",
        "warn": "⚠️ ",
        "err": "❌",
        "action": "📡",
        "wait": "⏳",
        "stop": "🛑",
        "start": "▶️",
    }
    icon = icons.get(level, "ℹ️ ")
    print(f"[{_now()}] {icon} [{context}] {message}")


def step(context: str, message: str) -> None:
    """Adım bildirimi (eylem)."""
    status(context, message, level="action")


def ok(context: str, message: str) -> None:
    status(context, message, level="ok")


def warn(context: str, message: str) -> None:
    status(context, message, level="warn")


def err(context: str, message: str) -> None:
    status(context, message, level="err")


def wait(context: str, message: str) -> None:
    status(context, message, level="wait")


