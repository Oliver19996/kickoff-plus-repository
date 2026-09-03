from __future__ import annotations

import re

TRANSFER_WORDS = (
    "transfer",
    "signing",
    "signs",
    "loan",
    "移籍",
    "獲得",
    "放出",
    "加入",
    "契約",
)
GOSSIP_WORDS = (
    "gossip",
    "rumour",
    "rumor",
    "affair",
    "dating",
    "private",
    "nightlife",
    "噂",
    "熱愛",
    "交際",
    "私生活",
    "結婚",
    "離婚",
    "スキャンダル",
)
MATCH_WORDS = (
    "result",
    "win",
    "defeat",
    "draw",
    "match",
    "score",
    "kick-off",
    "kickoff",
    "試合",
    "速報",
    "勝利",
    "敗戦",
    "引き分け",
    "得点",
)
NICHE_WORDS = (
    "tactical",
    "tactics",
    "analysis",
    "xG",
    "pressing",
    "特集",
    "戦術",
    "分析",
    "深掘り",
    "データ",
    "解説",
)

LEAGUE_HINTS = {
    "pl": ("premier league", "プレミア", "epl", "manchester", "liverpool", "arsenal", "chelsea", "tottenham"),
    "laliga": ("la liga", "laliga", "リーガ", "real madrid", "barcelona", "atletico", "アトレティコ", "バルサ"),
    "bundesliga": ("bundesliga", "ブンデス", "bayern", "dortmund", "leverkusen"),
    "j1": ("j-league", "jリーグ", "j1", "マリノス", "川崎", "浦和", "鹿島", "ガンバ", "セレッソ"),
}


def classify_article(title: str, summary: str = "") -> tuple[str, bool]:
    text = f"{title} {summary}".lower()
    if any(word.lower() in text for word in GOSSIP_WORDS):
        return "gossip", True
    if any(word.lower() in text for word in TRANSFER_WORDS):
        rumor = any(w in text for w in ("rumor", "rumour", "噂", "報道", "interest", "linked"))
        return "transfer", rumor
    if any(word.lower() in text for word in NICHE_WORDS):
        return "niche", False
    if any(word.lower() in text for word in MATCH_WORDS):
        return "match", False
    return "other", False


def detect_league(title: str, summary: str = "") -> str:
    text = f"{title} {summary}".lower()
    for slug, hints in LEAGUE_HINTS.items():
        if any(hint in text for hint in hints):
            return slug
    return "world"


def rumor_heat(title: str, peer_titles: list[str]) -> float:
    tokens = set(re.findall(r"[A-Za-z一-龥ぁ-んァ-ン]{3,}", title.lower()))
    if not tokens:
        return 0.2
    hits = 0
    for peer in peer_titles:
        if peer == title:
            continue
        peer_tokens = set(re.findall(r"[A-Za-z一-龥ぁ-んァ-ン]{3,}", peer.lower()))
        if len(tokens & peer_tokens) >= 2:
            hits += 1
    if hits >= 3:
        return 0.9
    if hits >= 1:
        return 0.55
    return 0.25


def heat_label(score: float) -> str:
    if score >= 0.8:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"
