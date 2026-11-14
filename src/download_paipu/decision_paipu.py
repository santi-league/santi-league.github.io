#!/usr/bin/env python3
"""Download and convert the finals listed in decision_links.txt.

Each season heading (for example ``s1``) routes subsequent links to that
season's finals folder. Finals never pass through the regular-season folders.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from src.convert_rico_to_tenhou import convert_rico_format_to_tenhou
from src.download_paipu.rico import RicochetDownloader
from src.s_league.config import SEASONS


ROOT = Path(__file__).resolve().parents[2]
LINKS_FILE = ROOT / "decision_links.txt"
RAW_FOLDER = ROOT / "downloaded_paipu" / "decision"
PAIPU_ID = re.compile(
    r"^(\d{6}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:_a\d+)?$",
    re.IGNORECASE,
)
SEASON_ID = re.compile(r"s\d+", re.IGNORECASE)


def parse_decision_links(path=LINKS_FILE):
    """Return (season_id, full_url, paipu_id) entries in file order."""
    entries = []
    seen = set()
    season_id = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if SEASON_ID.fullmatch(line):
            season_id = line.lower()
            if season_id not in SEASONS or not SEASONS[season_id].get("finals_folder"):
                raise ValueError(f"{path.name}:{line_number}: 未配置 {season_id} 的决定战目录")
            continue

        if season_id is None:
            raise ValueError(f"{path.name}:{line_number}: 请先写赛季标记，例如 s1")

        for prefix in ("雀魂牌譜:", "雀魂牌谱:"):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break

        parsed = urlsplit(line)
        paipu_values = parse_qs(parsed.query).get("paipu", [])
        match = PAIPU_ID.fullmatch(paipu_values[0]) if len(paipu_values) == 1 else None
        if (parsed.scheme != "https" or parsed.netloc != "game.maj-soul.com"
                or parsed.path != "/1/" or not match):
            raise ValueError(f"{path.name}:{line_number}: 无效的雀魂牌谱链接")

        paipu_id = match.group(1).lower()
        key = (season_id, paipu_id)
        if key not in seen:
            entries.append((season_id, line, paipu_id))
            seen.add(key)

    return entries


def write_json(path, data):
    """Write a JSON file atomically so an interrupted run cannot be cached."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(data, output, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporary, path)


def import_decision_links(path=LINKS_FILE):
    if not path.is_file():
        print("未找到 decision_links.txt，跳过决定战牌谱")
        return 0

    entries = parse_decision_links(path)
    if not entries:
        print("decision_links.txt 中没有决定战牌谱")
        return 0

    downloader = None
    imported = 0
    failed = 0

    needs_network = any(
        not (ROOT / SEASONS[season_id]["finals_folder"] / f"{paipu_id}.json").is_file()
        and not (RAW_FOLDER / season_id / f"{paipu_id}.json").is_file()
        for season_id, _, paipu_id in entries
    )
    if needs_network:
        username = os.environ.get("RICOCHET_USERNAME")
        password = os.environ.get("RICOCHET_PASSWORD")
        if not username or not password:
            print("决定战下载失败：缺少 RICOCHET_USERNAME 或 RICOCHET_PASSWORD", file=sys.stderr)
            return 1
        try:
            downloader = RicochetDownloader()
            downloader.login(username, password)
        except Exception as error:
            if downloader is not None:
                downloader.close()
            print(f"决定战登录失败：{error}", file=sys.stderr)
            return 1

    try:
        for index, (season_id, url, paipu_id) in enumerate(entries, 1):
            raw_path = RAW_FOLDER / season_id / f"{paipu_id}.json"
            finals_path = ROOT / SEASONS[season_id]["finals_folder"] / f"{paipu_id}.json"
            label = f"[{index}/{len(entries)}] {season_id} {paipu_id}"

            try:
                if finals_path.is_file():
                    print(f"{label}: 已存在")
                    continue

                if raw_path.is_file():
                    with raw_path.open(encoding="utf-8") as source:
                        rico_data = json.load(source)
                else:
                    print(f"{label}: 下载中")
                    rico_data = downloader.download(url)
                    write_json(raw_path, rico_data)
                    time.sleep(0.5)

                tenhou_data = convert_rico_format_to_tenhou(
                    rico_data, paipu_id=paipu_id, rule_type=SEASONS[season_id]["rule_type"]
                )
                if len(tenhou_data.get("name", [])) != 4 or len(tenhou_data.get("sc", [])) != 8:
                    raise ValueError("决定战牌谱缺少四名选手的完整成绩")
                tenhou_data["source_url"] = url
                write_json(finals_path, tenhou_data)
                print(f"{label}: 已导入 {finals_path.relative_to(ROOT)}")
                imported += 1
            except Exception as error:
                print(f"{label}: 失败：{error}", file=sys.stderr)
                failed += 1
    finally:
        if downloader is not None:
            downloader.close()

    print(f"决定战牌谱：{len(entries)} 条，新增 {imported} 条，失败 {failed} 条")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(import_decision_links())
    except (OSError, ValueError) as error:
        print(f"决定战链接读取失败：{error}", file=sys.stderr)
        sys.exit(1)
