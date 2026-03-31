from __future__ import annotations

import html
import json
import re
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "app_data.json"

app = Flask(__name__)
app.secret_key = "tavernkeeper-dev-secret"

PROTOTYPE_SEED_USERS = [
    {
        "email": "test@test.com",
        "display_name": "DM",
        "password": "123456",
        "role": "dm",
    },
    {
        "email": "test2@test.com",
        "display_name": "Player",
        "password": "123456",
        "role": "player",
    },
]


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    default_data = {
        "users": [],
        "campaigns": [],
        "memberships": [],
        "surveys": [],
        "announcements": [],
        "notes": [],
        "wiki_pages": [],
        "quest_acceptances": [],
    }
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(default_data, indent=2), encoding="utf-8")
        return

    existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    changed = False
    for key, value in default_data.items():
        if key not in existing:
            existing[key] = value
            changed = True

    membership_defaults = {
        "notable_proficiencies": "",
        "death_save_successes": "0",
        "death_save_failures": "0",
    }
    for membership in existing.get("memberships", []):
        for key, value in membership_defaults.items():
            if key not in membership:
                membership[key] = value
                changed = True

    for page in existing.get("wiki_pages", []):
        page_defaults = {
            "world_category": "",
            "subtitle": "",
            "summary": "",
            "image_url": "",
            "tags": "",
            "status": "published",
            "visibility": "all_players",
            "visible_user_ids": [],
            "detail_groups": [],
            "related_entry_titles": "",
        }
        for key, value in page_defaults.items():
            if key not in page:
                page[key] = value
                changed = True

    for campaign in existing.get("campaigns", []):
        if "world_editor_presets" not in campaign:
            campaign["world_editor_presets"] = {}
            changed = True

    existing_emails = {user["email"].lower() for user in existing["users"]}
    for seed_user in PROTOTYPE_SEED_USERS:
        if seed_user["email"].lower() in existing_emails:
            continue
        existing["users"].append(
            {
                "id": str(uuid.uuid4()),
                "email": seed_user["email"],
                "display_name": seed_user["display_name"],
                "password_hash": generate_password_hash(seed_user["password"]),
                "role": seed_user["role"],
            }
        )
        changed = True

    if changed:
        DATA_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def load_data() -> dict[str, list[dict[str, Any]]]:
    ensure_data_file()
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_data(data: dict[str, list[dict[str, Any]]]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_invite_code() -> str:
    return f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"


def get_user_by_id(data: dict[str, list[dict[str, Any]]], user_id: str) -> dict[str, Any] | None:
    return next((user for user in data["users"] if user["id"] == user_id), None)


def get_user_by_email(data: dict[str, list[dict[str, Any]]], email: str) -> dict[str, Any] | None:
    return next((user for user in data["users"] if user["email"].lower() == email.lower()), None)


def get_user_by_login(data: dict[str, list[dict[str, Any]]], login_value: str) -> dict[str, Any] | None:
    normalized = login_value.strip().lower()
    return next(
        (
            user
            for user in data["users"]
            if user["email"].lower() == normalized or user["display_name"].lower() == normalized
        ),
        None,
    )


def get_campaign_for_dm(data: dict[str, list[dict[str, Any]]], user_id: str) -> dict[str, Any] | None:
    return next((campaign for campaign in data["campaigns"] if campaign["dm_user_id"] == user_id), None)


def get_dm_campaigns(data: dict[str, list[dict[str, Any]]], user_id: str) -> list[dict[str, Any]]:
    return [campaign for campaign in data["campaigns"] if campaign["dm_user_id"] == user_id]


def get_campaign_by_id(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> dict[str, Any] | None:
    return next((campaign for campaign in data["campaigns"] if campaign["id"] == campaign_id), None)


def get_campaign_by_invite(data: dict[str, list[dict[str, Any]]], invite_code: str) -> dict[str, Any] | None:
    normalized = invite_code.strip().upper()
    return next((campaign for campaign in data["campaigns"] if campaign["invite_code"] == normalized), None)


def get_membership(data: dict[str, list[dict[str, Any]]], campaign_id: str, user_id: str) -> dict[str, Any] | None:
    return next(
        (
            membership
            for membership in data["memberships"]
            if membership["campaign_id"] == campaign_id and membership["user_id"] == user_id
        ),
        None,
    )


def get_membership_by_id(data: dict[str, list[dict[str, Any]]], membership_id: str) -> dict[str, Any] | None:
    return next((membership for membership in data["memberships"] if membership["id"] == membership_id), None)


def get_player_memberships(data: dict[str, list[dict[str, Any]]], user_id: str) -> list[dict[str, Any]]:
    return [membership for membership in data["memberships"] if membership["user_id"] == user_id]


def get_campaign_announcements(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, Any]]:
    return [item for item in data["announcements"] if item["campaign_id"] == campaign_id]


def get_campaign_notes(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, Any]]:
    return [item for item in data["notes"] if item["campaign_id"] == campaign_id]


def get_campaign_wiki_pages(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, Any]]:
    return [item for item in data["wiki_pages"] if item["campaign_id"] == campaign_id]


def get_wiki_page_by_id(data: dict[str, list[dict[str, Any]]], page_id: str) -> dict[str, Any] | None:
    return next((page for page in data["wiki_pages"] if page["id"] == page_id), None)


def get_campaign_player_targets(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for membership in data["memberships"]:
        if membership["campaign_id"] != campaign_id:
            continue
        user = get_user_by_id(data, membership["user_id"])
        if not user or user.get("role") != "player":
            continue
        targets.append(
            {
                "user_id": membership["user_id"],
                "membership_id": membership["id"],
                "display_name": user["display_name"],
                "character_name": membership.get("character_name", "Unknown Character"),
            }
        )
    return sorted(targets, key=lambda item: (item["display_name"].lower(), item["character_name"].lower()))


def build_character_wiki_content(membership: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {membership.get('character_name', 'Unnamed Character')}",
            "",
            f"Level: {membership.get('level') or 'Unknown'}",
            f"Class: {membership.get('class_name') or 'Unknown'}",
            f"Subclass: {membership.get('subclass') or 'Unknown'}",
            f"Species: {membership.get('species') or 'Unknown'}",
            f"Background: {membership.get('background') or 'Unknown'}",
            f"Notable Proficiencies: {membership.get('notable_proficiencies') or 'Unknown'}",
            f"Armor Class: {membership.get('armor_class') or 'Unknown'}",
            f"Speed: {membership.get('speed') or 'Unknown'}",
            f"Max Hit Points: {membership.get('max_hit_points') or 'Unknown'}",
            f"Current Hit Points: {membership.get('current_hit_points') or 'Unknown'}",
            f"Temporary Hit Points: {membership.get('temp_hit_points') or 'Unknown'}",
            f"Passive Perception: {membership.get('passive_perception') or 'Unknown'}",
            f"Passive Investigation: {membership.get('passive_investigation') or 'Unknown'}",
            f"Passive Insight: {membership.get('passive_insight') or 'Unknown'}",
            f"Initiative Bonus: {membership.get('initiative_bonus') or 'Unknown'}",
            f"Proficiency Bonus: {membership.get('proficiency_bonus') or 'Unknown'}",
            "",
            "## Ability Scores",
            f"Strength: {membership.get('strength') or 'Unknown'}",
            f"Dexterity: {membership.get('dexterity') or 'Unknown'}",
            f"Constitution: {membership.get('constitution') or 'Unknown'}",
            f"Intelligence: {membership.get('intelligence') or 'Unknown'}",
            f"Wisdom: {membership.get('wisdom') or 'Unknown'}",
            f"Charisma: {membership.get('charisma') or 'Unknown'}",
        ]
    )


def get_character_notes(data: dict[str, list[dict[str, Any]]], campaign_id: str, user_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in data["notes"]
        if item["campaign_id"] == campaign_id and item["author_user_id"] == user_id
    ]


def has_completed_onboarding(data: dict[str, list[dict[str, Any]]], campaign_id: str, user_id: str) -> bool:
    return any(
        item["campaign_id"] == campaign_id and item["user_id"] == user_id
        for item in data["surveys"]
    )


def has_completed_character_sheet(membership: dict[str, Any]) -> bool:
    required_fields = (
        "class_name",
        "subclass",
        "level",
        "armor_class",
        "speed",
        "passive_perception",
        "passive_investigation",
        "passive_insight",
        "initiative_bonus",
        "proficiency_bonus",
    )
    return all(str(membership.get(field, "")).strip() for field in required_fields)


def parse_ability_score(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def ability_modifier(value: Any) -> str:
    score = parse_ability_score(value)
    if score is None:
        return "—"
    modifier = (score - 10) // 2
    return f"{modifier:+d}"


def build_ability_cells(membership: dict[str, Any]) -> list[dict[str, str]]:
    ability_order = [
        ("STR", "strength"),
        ("DEX", "dexterity"),
        ("CON", "constitution"),
        ("INT", "intelligence"),
        ("WIS", "wisdom"),
        ("CHA", "charisma"),
    ]
    cells: list[dict[str, str]] = []
    for label, field in ability_order:
        raw_value = str(membership.get(field, "")).strip()
        cells.append(
            {
                "label": label,
                "score": raw_value or "—",
                "modifier": ability_modifier(raw_value),
            }
        )
    return cells


def parse_notable_proficiencies(raw_value: Any) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in str(raw_value or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = [part.strip() for part in cleaned.split("|")]
        name = parts[0] if parts else cleaned
        tier = parts[1] if len(parts) > 1 and parts[1] else "Proficient"
        modifier = parts[2] if len(parts) > 2 and parts[2] else ""
        entries.append(
            {
                "name": name,
                "tier": tier,
                "modifier": modifier,
            }
        )
    return entries


def proficiency_modifier_value(modifier: str) -> int:
    cleaned = str(modifier or "").strip().replace(" ", "")
    if not cleaned:
        return -99
    try:
        return int(cleaned)
    except ValueError:
        return -99


def build_summary_notable_proficiencies(raw_value: Any, limit: int = 4) -> list[dict[str, str]]:
    entries = parse_notable_proficiencies(raw_value)
    ranked = sorted(
        entries,
        key=lambda item: (
            proficiency_modifier_value(item.get("modifier", "")),
            1 if item.get("tier", "").strip().lower() == "expertise" else 0,
            item.get("name", "").lower(),
        ),
        reverse=True,
    )
    return ranked[:limit]


def parse_counter(value: Any, *, minimum: int = 0, maximum: int = 3) -> int:
    try:
        numeric = int(str(value).strip())
    except (TypeError, ValueError):
        numeric = minimum
    return max(minimum, min(maximum, numeric))


WIKI_LINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\[\]]+)\]\((https?://[^)\s]+)\)")
INLINE_MARKUP_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]|\[([^\[\]]+)\]\((https?://[^)\s]+)\)|\*\*([^*]+)\*\*|_([^_]+)_")
MEDIA_BLOCK_PATTERN = re.compile(r"^\[(https?://[^\]]+)\]$")
ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+")


def render_inline_markup(content: str, data: dict[str, list[dict[str, Any]]] | None = None, campaign_id: str | None = None) -> str:
    raw_text = str(content or "")

    pieces: list[str] = []
    cursor = 0
    for match in INLINE_MARKUP_PATTERN.finditer(raw_text):
        pieces.append(html.escape(raw_text[cursor:match.start()]))
        world_target = match.group(1)
        markdown_text = match.group(2)
        markdown_href = match.group(3)
        bold_text = match.group(4)
        italic_text = match.group(5)

        if world_target is not None:
            target = world_target.strip()
            page = None
            viewer = getattr(g, "user", None)
            if data and campaign_id:
                page = next(
                    (
                        item
                        for item in get_campaign_wiki_pages(data, campaign_id)
                        if item.get("title", "").strip().lower() == target.lower()
                        and (viewer is None or can_user_view_world_page(data, viewer, item))
                    ),
                    None,
                )
            if page:
                href = f"/world/{page['id']}"
                pieces.append(f'<a class="card-title-link inline-world-link" href="{href}">{html.escape(page["title"])}</a>')
            else:
                pieces.append(html.escape(f"[[{target}]]"))
        elif markdown_text is not None and markdown_href is not None:
            safe_href = html.escape(markdown_href, quote=True)
            pieces.append(
                f'<a class="inline-world-link" href="{safe_href}" target="_blank" rel="noreferrer">{html.escape(markdown_text)}</a>'
            )
        elif bold_text is not None:
            pieces.append(f"<strong>{html.escape(bold_text)}</strong>")
        elif italic_text is not None:
            pieces.append(f"<em>{html.escape(italic_text)}</em>")
        cursor = match.end()
    pieces.append(html.escape(raw_text[cursor:]))
    return "".join(pieces)


def is_safe_media_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_image_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"))


def is_video_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith((".mp4", ".webm", ".ogg", ".mov", ".m4v"))


def get_video_embed_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        video_id = parse_qs(parsed.query).get("v", [""])[0].strip()
        if video_id:
            return f"https://www.youtube.com/embed/{html.escape(video_id, quote=True)}"
    if "youtu.be" in host:
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/embed/{html.escape(video_id, quote=True)}"
    if "vimeo.com" in host:
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id.isdigit():
            return f"https://player.vimeo.com/video/{video_id}"
    return None


def render_media_block(url: str) -> str:
    safe_url = html.escape(url, quote=True)
    link_html = f'<a class="inline-world-link" href="{safe_url}" target="_blank" rel="noreferrer">Open media</a>'
    if not is_safe_media_url(url):
        return f"<p>{link_html}</p>"
    if is_image_url(url):
        return (
            '<figure class="markdown-media markdown-image-block">'
            f'<img class="markdown-image" src="{safe_url}" alt="Embedded image" loading="lazy" />'
            "</figure>"
        )
    embed_url = get_video_embed_url(url)
    if embed_url:
        return (
            '<div class="markdown-media markdown-video-block">'
            f'<iframe class="markdown-video-frame" src="{embed_url}" '
            'title="Embedded video" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
            "</div>"
        )
    if is_video_url(url):
        return (
            '<div class="markdown-media markdown-video-block">'
            f'<video class="markdown-video" controls preload="metadata" src="{safe_url}"></video>'
            "</div>"
        )
    return f"<p>{link_html}</p>"


def render_wiki_markup(
    content: Any,
    data: dict[str, list[dict[str, Any]]] | None = None,
    campaign_id: str | None = None,
) -> str:
    lines = str(content or "").splitlines()
    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    ordered_list_items: list[str] = []
    blockquote_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(item.strip() for item in paragraph_lines if item.strip())
            blocks.append(f"<p>{render_inline_markup(text, data, campaign_id)}</p>")
            paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            rendered = "".join(f"<li>{item}</li>" for item in list_items)
            blocks.append(f"<ul>{rendered}</ul>")
            list_items = []

    def flush_ordered_list() -> None:
        nonlocal ordered_list_items
        if ordered_list_items:
            rendered = "".join(f"<li>{item}</li>" for item in ordered_list_items)
            blocks.append(f"<ol>{rendered}</ol>")
            ordered_list_items = []

    def flush_blockquote() -> None:
        nonlocal blockquote_lines
        if blockquote_lines:
            text = " ".join(item.strip() for item in blockquote_lines if item.strip())
            blocks.append(f"<blockquote><p>{render_inline_markup(text, data, campaign_id)}</p></blockquote>")
            blockquote_lines = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            continue

        media_match = MEDIA_BLOCK_PATTERN.match(stripped)
        if media_match:
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            blocks.append(render_media_block(media_match.group(1).strip()))
            continue

        if stripped in {"---", "***"}:
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            blocks.append('<hr class="markdown-rule" />')
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            blocks.append(f"<h4>{render_inline_markup(stripped[4:], data, campaign_id)}</h4>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            blocks.append(f"<h3>{render_inline_markup(stripped[3:], data, campaign_id)}</h3>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_blockquote()
            blocks.append(f"<h2>{render_inline_markup(stripped[2:], data, campaign_id)}</h2>")
            continue
        if stripped.startswith("> "):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            blockquote_lines.append(stripped[2:])
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            flush_ordered_list()
            flush_blockquote()
            list_items.append(render_inline_markup(stripped[2:], data, campaign_id))
            continue
        if ORDERED_LIST_PATTERN.match(stripped):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            ordered_list_items.append(render_inline_markup(ORDERED_LIST_PATTERN.sub("", stripped, count=1), data, campaign_id))
            continue

        flush_list()
        flush_ordered_list()
        flush_blockquote()
        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_list()
    flush_ordered_list()
    flush_blockquote()
    return "\n".join(blocks) if blocks else "<p>No article content has been added yet.</p>"


def build_related_wiki_pages(
    data: dict[str, list[dict[str, Any]]],
    campaign_id: str,
    current_page_id: str,
    *,
    user: dict[str, Any] | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    viewer = user or getattr(g, "user", None)
    pages = [
        page
        for page in get_campaign_wiki_pages(data, campaign_id)
        if page["id"] != current_page_id and (viewer is None or can_user_view_world_page(data, viewer, page))
    ]
    pages.sort(key=lambda page: (page.get("source", ""), page.get("title", "").lower()))
    return pages[:limit]


def get_active_campaign_for_user(data: dict[str, list[dict[str, Any]]], user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    if user["role"] == "dm":
        return get_active_dm_campaign(data, user["id"])
    membership = get_active_player_membership(data, user["id"])
    if membership is None:
        return None
    return get_campaign_by_id(data, membership["campaign_id"])


def get_visible_notes_for_player(
    data: dict[str, list[dict[str, Any]]], campaign_id: str, user_id: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in get_campaign_notes(data, campaign_id)
        if item["author_user_id"] == user_id or item.get("visibility", "private") == "shared"
    ]


def get_shared_notes_for_player(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in get_campaign_notes(data, campaign_id)
        if item.get("visibility", "private") == "shared"
    ]


def get_visible_notes_for_dm(
    data: dict[str, list[dict[str, Any]]], campaign_id: str, dm_user_id: str
) -> list[dict[str, Any]]:
    return list(get_campaign_notes(data, campaign_id))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_campaign_feed_items(
    data: dict[str, list[dict[str, Any]]],
    campaign_id: str,
    *,
    user_id: str | None = None,
    include_all_notes: bool = False,
) -> list[dict[str, Any]]:
    feed_items: list[dict[str, Any]] = []

    if user_id is None:
        broadcasts = get_campaign_announcements(data, campaign_id)
    else:
        broadcasts = get_visible_broadcasts_for_player(data, campaign_id, user_id)

    for item in broadcasts:
        if item.get("kind") == "Quest":
            continue
        feed_items.append(
            {
                "id": item["id"],
                "entry_type": "broadcast",
                "kind": item.get("kind", "Announcement"),
                "title": item["title"],
                "body": item["body"],
                "wiki_page_id": item.get("wiki_page_id"),
                "world_category": item.get("world_category", ""),
                "author_name": "Dungeon Master",
                "author_user_id": item.get("author_user_id"),
                "target_user_ids": item.get("target_user_ids") or ([] if not item.get("target_user_id") else [item["target_user_id"]]),
                "visibility": None,
                "created_at": item.get("created_at", ""),
                "rendered_body": render_wiki_markup(item.get("body", ""), data, campaign_id),
            }
        )

    notes = get_campaign_notes(data, campaign_id) if include_all_notes else get_shared_notes_for_player(data, campaign_id)
    for note in notes:
        feed_items.append(
            {
                "id": note["id"],
                "entry_type": "note",
                "kind": "Campaign Note",
                "title": note["title"],
                "body": note["body"],
                "wiki_page_id": None,
                "author_name": note.get("author_name", "Unknown Author"),
                "author_user_id": note.get("author_user_id"),
                "visibility": note.get("visibility", "private"),
                "created_at": note.get("created_at", ""),
                "rendered_body": render_wiki_markup(note.get("body", ""), data, campaign_id),
            }
        )

    return sorted(feed_items, key=lambda item: item.get("created_at", ""), reverse=True)


def user_can_access_campaign(data: dict[str, list[dict[str, Any]]], user: dict[str, Any], campaign_id: str) -> bool:
    if user["role"] == "dm":
        campaign = get_campaign_by_id(data, campaign_id)
        return campaign is not None and campaign["dm_user_id"] == user["id"]
    return get_membership(data, campaign_id, user["id"]) is not None


def can_user_view_world_page(
    data: dict[str, list[dict[str, Any]]],
    user: dict[str, Any],
    page: dict[str, Any],
) -> bool:
    if not user_can_access_campaign(data, user, page["campaign_id"]):
        return False

    if user["role"] == "dm":
        return True

    status = str(page.get("status", "published")).strip().lower()
    if status != "published":
        return False

    visibility = str(page.get("visibility", "all_players")).strip().lower()
    if visibility == "dm_only":
        return False
    if visibility == "selected_players":
        return user["id"] in {str(item) for item in page.get("visible_user_ids", [])}
    return True


def get_visible_campaign_wiki_pages(
    data: dict[str, list[dict[str, Any]]],
    campaign_id: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        page
        for page in get_campaign_wiki_pages(data, campaign_id)
        if can_user_view_world_page(data, user, page)
    ]


def get_world_page_visible_names(
    data: dict[str, list[dict[str, Any]]],
    campaign_id: str,
    user_ids: list[str] | None,
) -> list[str]:
    wanted = {str(item) for item in (user_ids or [])}
    if not wanted:
        return []
    names: list[str] = []
    for target in get_campaign_player_targets(data, campaign_id):
        if target["user_id"] in wanted:
            names.append(f"{target['display_name']} · {target['character_name']}")
    return names


def get_visible_broadcasts_for_player(
    data: dict[str, list[dict[str, Any]]], campaign_id: str, user_id: str
) -> list[dict[str, Any]]:
    broadcasts: list[dict[str, Any]] = []
    for item in get_campaign_announcements(data, campaign_id):
        targets = item.get("target_user_ids") or []
        legacy_target = item.get("target_user_id")
        if legacy_target and not targets:
            targets = [legacy_target]
        if targets and user_id not in targets:
            continue
        broadcasts.append(item)
    return broadcasts


def get_campaign_quests(data: dict[str, list[dict[str, Any]]], campaign_id: str) -> list[dict[str, Any]]:
    return [item for item in data["announcements"] if item["campaign_id"] == campaign_id and item.get("kind") == "Quest"]


def get_quest_acceptance(data: dict[str, list[dict[str, Any]]], quest_id: str, user_id: str) -> dict[str, Any] | None:
    return next(
        (
            acceptance
            for acceptance in data["quest_acceptances"]
            if acceptance["quest_id"] == quest_id and acceptance["user_id"] == user_id
        ),
        None,
    )


def get_broadcast_by_id(data: dict[str, list[dict[str, Any]]], broadcast_id: str) -> dict[str, Any] | None:
    return next((item for item in data["announcements"] if item["id"] == broadcast_id), None)


def get_active_dm_campaign(data: dict[str, list[dict[str, Any]]], user_id: str) -> dict[str, Any] | None:
    campaigns = get_dm_campaigns(data, user_id)
    if not campaigns:
        return None
    active_campaign_id = session.get("active_campaign_id")
    if active_campaign_id:
        match = next((campaign for campaign in campaigns if campaign["id"] == active_campaign_id), None)
        if match:
            return match
    return campaigns[0]


def get_active_player_membership(data: dict[str, list[dict[str, Any]]], user_id: str) -> dict[str, Any] | None:
    memberships = get_player_memberships(data, user_id)
    if not memberships:
        return None
    active_campaign_id = session.get("active_campaign_id")
    if active_campaign_id:
        match = next((membership for membership in memberships if membership["campaign_id"] == active_campaign_id), None)
        if match:
            return match
    return memberships[0]


def get_world_category_definitions() -> list[dict[str, str]]:
    return [
        {
            "key": "gods",
            "label": "Gods & Deities",
            "eyebrow": "Pantheon",
            "heading": "Gods, Saints, and Divine Powers",
            "description": "The divine forces, celestial patrons, and sacred figures that shape the setting.",
        },
        {
            "key": "places",
            "label": "Places",
            "eyebrow": "Atlas",
            "heading": "Regions, Realms, and Settlements",
            "description": "Continents, cities, islands, and other landmarks that define the world map.",
        },
        {
            "key": "factions",
            "label": "Factions",
            "eyebrow": "Power Blocs",
            "heading": "Organizations, Orders, and Alliances",
            "description": "Political groups, magical councils, churches, and other powers moving across the setting.",
        },
        {
            "key": "people",
            "label": "People",
            "eyebrow": "Dossiers",
            "heading": "Characters and Notable Figures",
            "description": "Important individuals, public profiles, and character-centered world entries.",
        },
        {
            "key": "flora-fauna",
            "label": "Flora & Fauna",
            "eyebrow": "Natural World",
            "heading": "Beasts, Creatures, and Wild Growth",
            "description": "Bestiary-style entries, rare creatures, and notable natural life across the setting.",
        },
        {
            "key": "history",
            "label": "History",
            "eyebrow": "Chronicle",
            "heading": "Timelines, Ages, and Major Events",
            "description": "Past ages, turning points, wars, disasters, and historical context for the campaign world.",
        },
        {
            "key": "culture",
            "label": "Culture",
            "eyebrow": "Peoples",
            "heading": "Peoples, Customs, and Shared Identity",
            "description": "Races, customs, traditions, social groups, and the cultures that make the world feel lived in.",
        },
        {
            "key": "misc",
            "label": "Misc",
            "eyebrow": "Archive",
            "heading": "Unsorted and Miscellaneous Entries",
            "description": "Useful world entries that do not yet fit a more specific shelf in the atlas.",
        },
    ]


def get_world_category_options() -> list[dict[str, str]]:
    return [{"key": item["key"], "label": item["label"]} for item in get_world_category_definitions() if item["key"] != "misc"]


def get_world_editor_preview_specs() -> dict[str, Any]:
    shared_sections = [
        {
            "title": "Identity",
            "description": "The baseline information every World Atlas entry should carry.",
            "fields": [
                {"label": "Entry Title", "type": "text", "value": "Aegis"},
                {"label": "Subtitle / Tagline", "type": "text", "value": "The Shieldbearer"},
                {"label": "World Atlas Section", "type": "select", "value": "Gods & Deities"},
                {"label": "Summary", "type": "textarea", "value": "A short overview that explains why this entry matters at a glance."},
            ],
        },
        {
            "title": "Presentation",
            "description": "Fields that shape how the entry appears across the atlas.",
            "fields": [
                {"label": "Cover Image URL", "type": "text", "value": "https://example.com/world-entry-cover.jpg"},
                {"label": "Gallery / Attachments", "type": "text", "value": "Drag in maps, portraits, handouts, or linked media."},
                {"label": "Related Entries", "type": "text", "value": "[[The Divine Pantheon of Aetheria]], [[Celestia]]"},
                {"label": "Tags", "type": "text", "value": "pantheon, shield, divine order"},
            ],
        },
        {
            "title": "Publication",
            "description": "Controls for authorship, visibility, and how the entry enters the canon.",
            "fields": [
                {"label": "Visibility", "type": "select", "value": "Visible To Campaign"},
                {"label": "Source", "type": "select", "value": "DM Atlas Editor"},
                {"label": "Canon Status", "type": "select", "value": "Official"},
                {"label": "Entry Body", "type": "textarea", "value": "# Overview\nUse the full editor for the rich article body, crosslinks, media, and structured sections."},
            ],
        },
    ]

    categories = [
        {
            "key": "gods",
            "label": "Gods & Deities",
            "eyebrow": "Pantheon",
            "summary": "Divine entries focus on worship, symbolism, myths, and relationships across the heavens.",
            "sample_title": "Aegis",
            "groups": [
                {
                    "title": "Divine Identity",
                    "fields": [
                        {
                            "label": "Domain / Portfolio",
                            "type": "text",
                            "value": "Protection, guardianship, oaths",
                            "options": ["Protection", "War", "Light", "Death", "Storm", "Knowledge", "Nature", "Forge", "Trickery", "Fate"],
                        },
                        {"label": "Titles / Epithets", "type": "text", "value": "The Shieldbearer, Keeper of the Last Wall"},
                        {"label": "Symbol", "type": "text", "value": "A gold shield crossed by a comet trail"},
                        {
                            "label": "Alignment / Disposition",
                            "type": "text",
                            "value": "Lawful Benevolent",
                            "options": ["Lawful Benevolent", "Neutral Benevolent", "Chaotic Benevolent", "Lawful Severe", "True Neutral", "Chaotic Hostile"],
                        },
                    ],
                },
                {
                    "title": "Worship & Myth",
                    "fields": [
                        {"label": "Clergy / Followers", "type": "text", "value": "Wardens, caravan guardians, oathbound knights"},
                        {"label": "Regions Of Worship", "type": "text", "value": "Celestia, stormbreak keeps, border shrines"},
                        {"label": "Rites / Holy Days", "type": "textarea", "value": "Night watch vigils, shield-anointing rites, oath renewals at dawn."},
                        {"label": "Allies / Rivals", "type": "text", "value": "Allied with Aurora, opposed by Thanatos"},
                    ],
                },
            ],
        },
        {
            "key": "places",
            "label": "Places",
            "eyebrow": "Atlas",
            "summary": "Location entries capture geography, governance, travel value, and what players will actually find there.",
            "sample_title": "The Whispering Isles",
            "groups": [
                {
                    "title": "Location Basics",
                    "fields": [
                        {
                            "label": "Place Type",
                            "type": "text",
                            "value": "Island Chain",
                            "options": ["Continent", "Kingdom", "City", "Village", "Island", "Island Chain", "Dungeon", "Landmark", "Plane", "District"],
                        },
                        {"label": "Region / Parent Location", "type": "text", "value": "Outer Maelstrom"},
                        {"label": "Government / Controller", "type": "text", "value": "Independent city-states and tidebound houses"},
                        {"label": "Population", "type": "text", "value": "Sparse coastal settlements and shipborne enclaves"},
                    ],
                },
                {
                    "title": "Travel & Texture",
                    "fields": [
                        {
                            "label": "Climate",
                            "type": "text",
                            "value": "Mist-heavy, storm-prone, humid",
                            "options": ["Arctic", "Temperate", "Tropical", "Desert", "Humid", "Storm-wracked", "Magically unstable", "Frozen", "Volcanic"],
                        },
                        {"label": "Landmarks", "type": "textarea", "value": "Blackglass reefs, moonlit harbors, drowned archways, whisper cliffs."},
                        {"label": "Resources / Trade", "type": "text", "value": "Pearls, stormsalt, rare inks, drifting timber"},
                        {"label": "Travel Notes", "type": "textarea", "value": "Safe passage requires local pilots and careful timing with the tide veils."},
                    ],
                },
            ],
        },
        {
            "key": "factions",
            "label": "Factions",
            "eyebrow": "Power Blocs",
            "summary": "Faction entries should make their purpose, reach, and threat legible in seconds.",
            "sample_title": "Celestial Council",
            "groups": [
                {
                    "title": "Power Structure",
                    "fields": [
                        {
                            "label": "Faction Type",
                            "type": "text",
                            "value": "Council",
                            "options": ["Council", "Government", "Religious Order", "Mage Circle", "Mercenary Company", "Criminal Syndicate", "Merchant Guild", "Secret Society"],
                        },
                        {"label": "Leader", "type": "text", "value": "High Chancellor Merrow Vale"},
                        {"label": "Headquarters", "type": "text", "value": "The Azure Citadel"},
                        {"label": "Territory / Influence", "type": "text", "value": "Celestia, sky ports, allied bastions"},
                    ],
                },
                {
                    "title": "Goals & Reputation",
                    "fields": [
                        {"label": "Goals", "type": "textarea", "value": "Preserve magical order, regulate skyway access, contain the Maelstrom's expansion."},
                        {"label": "Methods", "type": "text", "value": "Arcane law, diplomatic pressure, sanctioned expeditionary forces"},
                        {
                            "label": "Public Reputation",
                            "type": "text",
                            "value": "Necessary, distant, increasingly feared",
                            "options": ["Beloved", "Respected", "Necessary", "Distrusted", "Feared", "Hated"],
                        },
                        {"label": "Allies / Enemies", "type": "text", "value": "Allied with the Council of Archmages, tense with independent sky captains"},
                    ],
                },
            ],
        },
        {
            "key": "people",
            "label": "People",
            "eyebrow": "Dossiers",
            "summary": "People entries should balance fast dossier facts with enough texture for roleplay.",
            "sample_title": "Captain Ilyra Thorn",
            "groups": [
                {
                    "title": "Public Profile",
                    "fields": [
                        {"label": "Full Name", "type": "text", "value": "Captain Ilyra Thorn"},
                        {"label": "Aliases / Titles", "type": "text", "value": "The Reef Hawk"},
                        {"label": "Species", "type": "text", "value": "High Elf"},
                        {"label": "Role / Class", "type": "text", "value": "Skyship captain, rogue-adjacent fixer"},
                    ],
                },
                {
                    "title": "Story Hooks",
                    "fields": [
                        {"label": "Faction Affiliation", "type": "text", "value": "Independent, former Celestial Council courier"},
                        {
                            "label": "Status",
                            "type": "text",
                            "value": "Alive / Active",
                            "options": ["Alive / Active", "Missing", "Dead", "Unknown", "Retired", "Imprisoned"],
                        },
                        {"label": "Goals / Motivations", "type": "textarea", "value": "Clear old debts, protect her crew, uncover the truth behind the drowned route logs."},
                        {"label": "Relationships / Secrets", "type": "textarea", "value": "Still smuggles messages for a council contact she swore she cut ties with."},
                    ],
                },
            ],
        },
        {
            "key": "flora-fauna",
            "label": "Flora & Fauna",
            "eyebrow": "Natural World",
            "summary": "Creature and plant entries should help a DM run encounters, ecology, and discovery.",
            "sample_title": "Tempest Bloom",
            "groups": [
                {
                    "title": "Creature / Plant Profile",
                    "fields": [
                        {
                            "label": "Entry Type",
                            "type": "text",
                            "value": "Magical Flora",
                            "options": ["Beast", "Monster", "Plant", "Fungus", "Construct", "Celestial", "Fiend", "Magical Flora", "Magical Phenomenon"],
                        },
                        {"label": "Habitat", "type": "text", "value": "Cliff edges along storm channels"},
                        {"label": "Temperament / Behavior", "type": "text", "value": "Dormant until charged by lightning"},
                        {
                            "label": "Threat Level",
                            "type": "text",
                            "value": "Low To Moderate",
                            "options": ["Harmless", "Low", "Low To Moderate", "Moderate", "High", "Deadly"],
                        },
                    ],
                },
                {
                    "title": "Use In Play",
                    "fields": [
                        {"label": "Ecology / Diet", "type": "text", "value": "Feeds on ambient arcana and static charge"},
                        {"label": "Uses", "type": "text", "value": "Potion catalyst, ritual focus, sky-sail insulation"},
                        {"label": "Variants", "type": "text", "value": "Blueglass bloom, bloodstorm bloom"},
                        {"label": "Encounter Notes", "type": "textarea", "value": "Harvesting without grounding tools risks a volatile discharge."},
                    ],
                },
            ],
        },
        {
            "key": "history",
            "label": "History",
            "eyebrow": "Chronicle",
            "summary": "Historical entries should anchor events in time, place, cause, and consequence.",
            "sample_title": "The Fracture Of The Seventh Skyway",
            "groups": [
                {
                    "title": "Event Framework",
                    "fields": [
                        {
                            "label": "Event Type",
                            "type": "text",
                            "value": "Disaster",
                            "options": ["Disaster", "War", "Founding", "Coronation", "Schism", "Discovery", "Migration", "Age Transition"],
                        },
                        {"label": "Date / Era", "type": "text", "value": "Third Tempest Age, 417 A.M."},
                        {"label": "Location", "type": "text", "value": "The Azure Citadel and surrounding skyways"},
                        {"label": "Key Figures", "type": "text", "value": "Archmage Solenne, the Council's tidewrights"},
                    ],
                },
                {
                    "title": "Impact",
                    "fields": [
                        {"label": "Cause", "type": "textarea", "value": "An overdrawn ward lattice collided with the Tempest Core's surge cycle."},
                        {"label": "Outcome", "type": "textarea", "value": "Three skyways collapsed and trade routes were rerouted for a generation."},
                        {"label": "Consequences", "type": "textarea", "value": "It reshaped faction power, migration, and public trust in arcane governance."},
                        {"label": "Historical Significance", "type": "text", "value": "A turning point in Aetherian infrastructure and magical law"},
                    ],
                },
            ],
        },
        {
            "key": "culture",
            "label": "Culture",
            "eyebrow": "Peoples",
            "summary": "Culture entries explain how people live, celebrate, believe, and interpret the world.",
            "sample_title": "High Elves Of Celestia",
            "groups": [
                {
                    "title": "Cultural Identity",
                    "fields": [
                        {"label": "Culture / People Name", "type": "text", "value": "High Elves of Celestia"},
                        {"label": "Primary Regions", "type": "text", "value": "Celestia, the upper reaches, archive districts"},
                        {"label": "Language", "type": "text", "value": "Aetheric High Speech, Common"},
                        {"label": "Values / Beliefs", "type": "textarea", "value": "Legacy, refinement, stewardship, and the responsible shaping of magic."},
                    ],
                },
                {
                    "title": "Customs & Texture",
                    "fields": [
                        {"label": "Traditions", "type": "text", "value": "Sky lantern vigils, archive pledges, moonwake feasts"},
                        {"label": "Social Structure", "type": "text", "value": "Archive houses, mage lineages, civic orders"},
                        {"label": "Dress / Aesthetics", "type": "text", "value": "Layered silks, metal filigree, sigil embroidery"},
                        {"label": "Customs / Taboos", "type": "textarea", "value": "Breaking an oath in public is treated as a social death wound in most circles."},
                    ],
                },
            ],
        },
        {
            "key": "misc",
            "label": "Misc",
            "eyebrow": "Archive",
            "summary": "Misc entries stay flexible so loose ends can exist before they deserve a stricter structure.",
            "sample_title": "Blackglass Sigil Keys",
            "groups": [
                {
                    "title": "Flexible Entry Shell",
                    "fields": [
                        {"label": "Subtype", "type": "text", "value": "Artifact Cluster"},
                        {"label": "Primary Use", "type": "text", "value": "Unlocks sealed routes and hidden archive chambers"},
                        {"label": "Current Keeper", "type": "text", "value": "Unknown"},
                        {"label": "Open Questions", "type": "textarea", "value": "Who forged them, how many exist, and why do they resonate with the Tempest Core?"},
                    ],
                },
                {
                    "title": "Notes & Crosslinks",
                    "fields": [
                        {"label": "Related Entries", "type": "text", "value": "[[The Maelstrom]], [[Council Of Archmages]]"},
                        {"label": "Discovery Context", "type": "textarea", "value": "Recovered from a drowned relay under the shattered seventh skyway."},
                        {"label": "GM Notes", "type": "textarea", "value": "Useful for foreshadowing long before the party learns the full truth."},
                    ],
                },
            ],
        },
    ]

    return {"shared_sections": shared_sections, "categories": categories}


def editor_field_key(*parts: str) -> str:
    cleaned_parts = []
    for part in parts:
        cleaned = re.sub(r"[^a-z0-9]+", "_", str(part).strip().lower()).strip("_")
        if cleaned:
            cleaned_parts.append(cleaned)
    return "_".join(cleaned_parts)


def merge_world_editor_options(
    campaign: dict[str, Any] | None,
    preset_key: str,
    base_options: list[str] | None,
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()

    for option in base_options or []:
        cleaned = str(option).strip()
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(cleaned)

    presets = (campaign or {}).get("world_editor_presets", {}).get(preset_key, [])
    for option in presets:
        cleaned = str(option).strip()
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(cleaned)

    return values


def get_world_visibility_options() -> list[dict[str, str]]:
    return [
        {"value": "all_players", "label": "All Players"},
        {"value": "selected_players", "label": "Selected Players"},
        {"value": "dm_only", "label": "DM Only"},
    ]


def prepare_world_editor_category(
    category_key: str,
    page: dict[str, Any] | None = None,
    campaign: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    preview = get_world_editor_preview_specs()
    lookup = {item["key"]: item for item in preview["categories"]}
    category = lookup.get(category_key)
    if category is None:
        return None

    detail_lookup: dict[tuple[str, str], str] = {}
    for group in page.get("detail_groups", []) if page else []:
        for field in group.get("fields", []):
            detail_lookup[(group.get("title", ""), field.get("label", ""))] = str(field.get("value", ""))

    groups: list[dict[str, Any]] = []
    for group in category["groups"]:
        fields: list[dict[str, Any]] = []
        for field in group["fields"]:
            preset_key = editor_field_key(category["key"], group["title"], field["label"])
            fields.append(
                {
                    **field,
                    "name": preset_key,
                    "preset_key": preset_key,
                    "value": detail_lookup.get((group["title"], field["label"]), ""),
                    "placeholder": field.get("value", ""),
                    "options": merge_world_editor_options(campaign, preset_key, field.get("options", [])),
                }
            )
        groups.append({**group, "fields": fields})

    return {**category, "groups": groups}


def categorize_world_pages(pages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    categories: dict[str, list[dict[str, Any]]] = {item["key"]: [] for item in get_world_category_definitions()}
    explicit_keys = {item["key"] for item in get_world_category_definitions()}
    uncategorized_pages: list[dict[str, Any]] = []

    for page in pages:
        explicit_category = str(page.get("world_category", "")).strip()
        if explicit_category in explicit_keys and explicit_category != "misc":
            categories[explicit_category].append(page)
        else:
            uncategorized_pages.append(page)

    pages = uncategorized_pages
    page_lookup = {page["title"]: page for page in pages}
    pantheon_names = {
        "The Divine Pantheon of Aetheria",
        "Aegis", "Aquila", "Aurora", "Chronos", "Ignatius", "Lunara",
        "Nimbus", "Ororo", "Stellaris", "Sylvana", "Terra", "Thanatos",
    }
    place_names = {
        "Aetheria, Realm of the Maelstrom",
        "Continents of Aetheria",
        "Celestia", "Stormhold", "The Azure Citadel", "The Elysium Reach",
        "The Maelstrom", "The Whispering Isles",
    }
    faction_names = {"Factions of Aetheria", "Celestial Council", "Council Of Archmages", "The Divine Pantheon"}
    culture_names = {
        "Races of Aetheria",
        "Avis", "Dragonborn", "Dwarves", "Eternals", "Gnomes", "Goblins", "God",
        "Goliaths", "Haren", "High Elves", "Humans", "Leonin", "Orcs", "Satyrs", "Shadowkin Elves",
    }

    categories["gods"].extend(page_lookup[name] for name in sorted(pantheon_names) if name in page_lookup)
    categories["places"].extend(page_lookup[name] for name in sorted(place_names) if name in page_lookup)
    categories["factions"].extend(page_lookup[name] for name in sorted(faction_names) if name in page_lookup)
    categories["people"].extend(
        sorted(
            [page for page in pages if page.get("source") == "character_profile"],
            key=lambda page: page["title"].lower(),
        )
    )
    categories["culture"].extend(page_lookup[name] for name in sorted(culture_names) if name in page_lookup)

    used_titles = set()
    for items in categories.values():
        used_titles.update(page["title"] for page in items)
    categories["misc"].extend(sorted(
        [page for page in pages if page["title"] not in used_titles],
        key=lambda page: page["title"].lower(),
    ))
    for key, items in categories.items():
        categories[key] = sorted(items, key=lambda page: page["title"].lower())
    return categories


def build_world_entry_subheading(page: dict[str, Any]) -> str:
    explicit = str(page.get("subtitle", "")).strip()
    if explicit:
        return explicit

    content = str(page.get("content", "")).strip()
    if not content:
        return ""

    for line in content.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned and cleaned.lower() != str(page.get("title", "")).strip().lower():
            return cleaned[:88] + ("..." if len(cleaned) > 88 else "")
    return ""


def decorate_world_entries(
    data: dict[str, list[dict[str, Any]]],
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for page in pages:
        membership = get_membership_by_id(data, page.get("membership_id", "")) if page.get("membership_id") else None
        image_url = ""
        if membership and membership.get("portrait_url"):
            image_url = membership["portrait_url"]
        elif page.get("image_url"):
            image_url = str(page["image_url"]).strip()

        decorated.append(
            {
                **page,
                "image_url": image_url,
                "subheading": build_world_entry_subheading(page),
                "initial": (page.get("title", "?") or "?")[0].upper(),
            }
        )
    return decorated


def build_world_sidebar_nav(
    data: dict[str, list[dict[str, Any]]],
    campaign: dict[str, Any] | None,
    user: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not campaign or not user:
        return []

    pages = get_visible_campaign_wiki_pages(data, campaign["id"], user)
    categories = categorize_world_pages(pages)
    nav_items: list[dict[str, Any]] = []
    can_create = user.get("role") == "dm" and campaign.get("dm_user_id") == user.get("id")

    for spec in get_world_category_definitions():
        count = len(categories.get(spec["key"], []))
        nav_items.append(
            {
                "key": spec["key"],
                "label": spec["label"],
                "count": count,
                "href": url_for("world_category", category_key=spec["key"]),
                "editor_href": url_for("world_editor", category_key=spec["key"]) if can_create else "",
            }
        )
    return nav_items


@app.before_request
def load_current_user() -> None:
    data = load_data()
    user_id = session.get("user_id")
    g.user = get_user_by_id(data, user_id) if user_id else None


@app.context_processor
def inject_globals() -> dict[str, Any]:
    account_campaigns: list[dict[str, Any]] = []
    active_sidebar_campaign: dict[str, Any] | None = None
    active_sidebar_membership: dict[str, Any] | None = None
    drawer_character_notes: list[dict[str, Any]] = []
    sidebar_body_mode = "default"
    world_sidebar_nav: list[dict[str, Any]] = []

    if g.user:
        data = load_data()
        if g.user["role"] == "dm":
            campaigns = get_dm_campaigns(data, g.user["id"])
            account_campaigns = [{"id": campaign["id"], "name": campaign["name"]} for campaign in campaigns]
            active_sidebar_campaign = get_active_dm_campaign(data, g.user["id"])
        else:
            memberships = get_player_memberships(data, g.user["id"])
            active_sidebar_membership = get_active_player_membership(data, g.user["id"])
            for membership in memberships:
                campaign = get_campaign_by_id(data, membership["campaign_id"])
                if campaign:
                    account_campaigns.append(
                        {
                            "id": campaign["id"],
                            "name": campaign["name"],
                            "character_name": membership["character_name"],
                        }
                    )
            if active_sidebar_membership:
                active_sidebar_campaign = get_campaign_by_id(data, active_sidebar_membership["campaign_id"])
                drawer_character_notes = list(
                    reversed(get_character_notes(data, active_sidebar_membership["campaign_id"], g.user["id"]))
                )

        if request.endpoint in {"world_landing", "world_atlas", "world_category", "world_entry", "character_world_entry", "world_editor_preview", "world_editor"}:
            sidebar_body_mode = "world"
            world_sidebar_nav = build_world_sidebar_nav(data, active_sidebar_campaign, g.user)

    return {
        "current_user": g.user,
        "account_campaigns": account_campaigns,
        "active_sidebar_campaign": active_sidebar_campaign,
        "active_sidebar_membership": active_sidebar_membership,
        "drawer_character_notes": drawer_character_notes,
        "sidebar_body_mode": sidebar_body_mode,
        "world_sidebar_nav": world_sidebar_nav,
    }


def require_login():
    if g.user is None:
        return redirect(url_for("auth"))
    return None


def is_fetch_request() -> bool:
    return request.headers.get("X-Requested-With") == "fetch"


@app.route("/")
def home():
    if g.user is None:
        return redirect(url_for("auth"))
    if g.user["role"] == "dm":
        return redirect(url_for("dm_dashboard"))
    return redirect(url_for("player_home"))


@app.route("/auth", methods=["GET", "POST"])
def auth():
    data = load_data()
    active_tab = request.args.get("tab", "register")

    if request.method == "POST":
        form_type = request.form.get("form_type", "register")
        active_tab = form_type

        if form_type == "register":
            email = request.form.get("email", "").strip()
            display_name = request.form.get("display_name", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "player")

            if not email or not display_name or not password:
                flash("Please complete every registration field.", "error")
            elif get_user_by_email(data, email):
                flash("An account with that email already exists. Try logging in instead.", "error")
            else:
                user = {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "display_name": display_name,
                    "password_hash": generate_password_hash(password),
                    "role": role,
                }
                data["users"].append(user)
                save_data(data)
                session["user_id"] = user["id"]
                flash(f"{'DM' if role == 'dm' else 'Player'} account created successfully.", "success")
                return redirect(url_for("home"))
        else:
            login_value = request.form.get("login_identifier", "").strip()
            password = request.form.get("login_password", "")
            user = get_user_by_login(data, login_value)

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Those login details did not match an account.", "error")
            else:
                session["user_id"] = user["id"]
                flash(f"Welcome back, {user['display_name']}.", "success")
                return redirect(url_for("home"))

    return render_template("auth.html", active_tab=active_tab)


@app.route("/recover", methods=["GET", "POST"])
def recover():
    if request.method == "POST":
        flash("Password recovery is not wired to email yet, but this is where that flow will live.", "success")
        return redirect(url_for("auth", tab="login"))
    return render_template("recover.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth"))


@app.route("/settings")
def settings():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    return render_template("settings.html")


@app.route("/formatting-help")
def formatting_help():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    return render_template("formatting_help.html")


@app.route("/campaigns")
def campaigns_page():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    selected_campaign_id = request.args.get("campaign_id", "").strip()

    if g.user["role"] == "dm":
        campaigns = get_dm_campaigns(data, g.user["id"])
        selected_campaign = (
            get_campaign_by_id(data, selected_campaign_id)
            if selected_campaign_id
            else get_active_dm_campaign(data, g.user["id"])
        )
    else:
        memberships = get_player_memberships(data, g.user["id"])
        campaigns = []
        for membership in memberships:
            campaign = get_campaign_by_id(data, membership["campaign_id"])
            if campaign is None:
                continue
            campaigns.append(
                {
                    **campaign,
                    "character_name": membership.get("character_name"),
                    "membership_id": membership.get("id"),
                    "has_completed_onboarding": has_completed_onboarding(data, membership["campaign_id"], g.user["id"]),
                    "has_completed_character_sheet": has_completed_character_sheet(membership),
                }
            )
        selected_campaign = (
            next((campaign for campaign in campaigns if campaign["id"] == selected_campaign_id), None)
            if selected_campaign_id
            else (campaigns[0] if campaigns else None)
        )

    return render_template("campaigns.html", campaigns=campaigns, selected_campaign=selected_campaign)


@app.route("/campaigns/<campaign_id>/leave", methods=["POST"])
def leave_campaign(campaign_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_membership(data, campaign_id, g.user["id"])
    if membership is None:
        flash("That campaign membership could not be found.", "error")
        return redirect(url_for("campaigns_page"))

    membership_id = membership["id"]
    data["memberships"] = [
        item for item in data["memberships"]
        if not (item["campaign_id"] == campaign_id and item["user_id"] == g.user["id"])
    ]
    data["surveys"] = [
        item for item in data["surveys"]
        if not (item["campaign_id"] == campaign_id and item["user_id"] == g.user["id"])
    ]
    data["notes"] = [
        item for item in data["notes"]
        if not (item["campaign_id"] == campaign_id and item["author_user_id"] == g.user["id"])
    ]
    data["quest_acceptances"] = [
        item for item in data["quest_acceptances"]
        if not (item["campaign_id"] == campaign_id and item["user_id"] == g.user["id"])
    ]
    data["wiki_pages"] = [
        item for item in data["wiki_pages"]
        if item.get("membership_id") != membership_id
    ]
    save_data(data)

    if session.get("active_campaign_id") == campaign_id:
        remaining_memberships = get_player_memberships(load_data(), g.user["id"])
        session["active_campaign_id"] = remaining_memberships[0]["campaign_id"] if remaining_memberships else None

    flash("You have left that campaign.", "success")
    return redirect(url_for("campaigns_page"))


@app.route("/wiki")
def wiki_index():
    return redirect(url_for("world_landing"))


@app.route("/world")
def world_landing():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    campaign = get_active_campaign_for_user(data, g.user)
    pages = get_visible_campaign_wiki_pages(data, campaign["id"], g.user) if campaign else []
    return render_template(
        "world_landing.html",
        pages=decorate_world_entries(data, pages),
        campaign=campaign,
    )


@app.route("/codex")
def codex_landing():
    return redirect(url_for("world_landing"))


@app.route("/world/atlas")
def world_atlas():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    campaign = get_active_campaign_for_user(data, g.user)
    pages = get_visible_campaign_wiki_pages(data, campaign["id"], g.user) if campaign else []
    page_lookup = {page["title"]: page for page in pages}
    featured_page = page_lookup.get("Aetheria, Realm of the Maelstrom")
    categories = categorize_world_pages(pages)

    collection_titles = [
        "The Divine Pantheon of Aetheria",
        "Continents of Aetheria",
        "Factions of Aetheria",
        "Races of Aetheria",
    ]
    collections = [page_lookup[title] for title in collection_titles if title in page_lookup]
    collection_set = {page["title"] for page in collections}
    recent_entries = sorted(
        [
            page
            for page in pages
            if page["title"] not in collection_set
            and page is not featured_page
            and page.get("source") == "kanka_import"
        ],
        key=lambda page: page["title"].lower(),
    )[:12]

    return render_template(
        "world_atlas.html",
        campaign=campaign,
        featured_page=featured_page,
        collections=collections,
        pantheon_entries=categories["gods"],
        continent_entries=categories["places"],
        faction_entries=categories["factions"],
        race_entries=categories["culture"],
        character_entries=categories["people"],
        flora_fauna_entries=categories["flora-fauna"],
        history_entries=categories["history"],
        culture_entries=categories["culture"],
        misc_entries=categories["misc"],
        recent_entries=recent_entries,
    )


@app.route("/world/category/<category_key>")
def world_category(category_key: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    definitions = {item["key"]: item for item in get_world_category_definitions()}
    if category_key not in definitions:
        flash("That world section does not exist.", "error")
        return redirect(url_for("world_atlas"))

    data = load_data()
    campaign = get_active_campaign_for_user(data, g.user)
    pages = get_visible_campaign_wiki_pages(data, campaign["id"], g.user) if campaign else []
    categories = categorize_world_pages(pages)
    category = definitions[category_key]
    entries = decorate_world_entries(data, categories.get(category_key, []))
    featured_entry = entries[0] if entries else None

    return render_template(
        "world_category.html",
        campaign=campaign,
        category=category,
        entries=entries,
        featured_entry=featured_entry,
    )


@app.route("/world/editor-preview")
def world_editor_preview():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    campaign = get_active_campaign_for_user(data, g.user)
    preview = get_world_editor_preview_specs()
    categories = preview["categories"]
    active_category_key = request.args.get("category", categories[0]["key"] if categories else "gods").strip()
    category_lookup = {item["key"]: item for item in categories}
    if active_category_key not in category_lookup:
        active_category_key = categories[0]["key"] if categories else "gods"

    return render_template(
        "world_editor_preview.html",
        campaign=campaign,
        shared_sections=preview["shared_sections"],
        preview_categories=categories,
        active_preview_category=category_lookup.get(active_category_key),
    )


@app.route("/world/editor/<category_key>", methods=["GET", "POST"])
def world_editor(category_key: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "dm":
        flash("Only the DM can author World Atlas entries.", "error")
        return redirect(url_for("world_atlas"))

    data = load_data()
    campaign = get_active_dm_campaign(data, g.user["id"])
    if campaign is None:
        flash("Create or switch to a campaign before authoring atlas entries.", "error")
        return redirect(url_for("campaigns_page"))

    page_id = request.args.get("page_id", "").strip() or request.form.get("page_id", "").strip()
    page = get_wiki_page_by_id(data, page_id) if page_id else None
    if page is not None and page.get("campaign_id") != campaign["id"]:
        page = None

    if page is not None and page.get("world_category") in {item["key"] for item in get_world_category_definitions()}:
        category_key = page.get("world_category", category_key)

    category = prepare_world_editor_category(category_key, page, campaign)
    if category is None:
        flash("That World Atlas section does not exist.", "error")
        return redirect(url_for("world_atlas"))

    player_targets = get_campaign_player_targets(data, campaign["id"])
    visibility_options = get_world_visibility_options()
    selected_user_ids = set(str(item) for item in (page.get("visible_user_ids", []) if page else []))

    form_values = {
        "title": page.get("title", "") if page else "",
        "subtitle": page.get("subtitle", "") if page else "",
        "summary": page.get("summary", "") if page else "",
        "image_url": page.get("image_url", "") if page else "",
        "tags": page.get("tags", "") if page else "",
        "related_entry_titles": page.get("related_entry_titles", "") if page else "",
        "body": page.get("content", "") if page else "",
        "visibility": page.get("visibility", "all_players") if page else "all_players",
    }

    if request.method == "POST":
        form_values = {
            "title": request.form.get("title", "").strip(),
            "subtitle": request.form.get("subtitle", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "image_url": request.form.get("image_url", "").strip(),
            "tags": request.form.get("tags", "").strip(),
            "related_entry_titles": request.form.get("related_entry_titles", "").strip(),
            "body": request.form.get("body", "").strip(),
            "visibility": request.form.get("visibility", "all_players").strip(),
        }
        if form_values["visibility"] not in {item["value"] for item in visibility_options}:
            form_values["visibility"] = "all_players"

        selected_user_ids = {
            target["user_id"]
            for target in player_targets
            if target["user_id"] in request.form.getlist("visible_user_ids")
        }

        detail_groups: list[dict[str, Any]] = []
        campaign.setdefault("world_editor_presets", {})
        for group in category["groups"]:
            saved_fields: list[dict[str, str]] = []
            for field in group["fields"]:
                value = request.form.get(field["name"], "").strip()
                field["value"] = value
                if value and field.get("options"):
                    existing_options = {str(item).strip().lower() for item in field["options"]}
                    if value.lower() not in existing_options:
                        stored = campaign["world_editor_presets"].setdefault(field["preset_key"], [])
                        if value.lower() not in {str(item).strip().lower() for item in stored}:
                            stored.append(value)
                if value:
                    saved_fields.append({"label": field["label"], "value": value})
            if saved_fields:
                detail_groups.append({"title": group["title"], "fields": saved_fields})

        action = request.form.get("submit_action", "draft").strip().lower()
        status = "published" if action == "publish" else "draft"

        if not form_values["title"]:
            flash("Entry title is required.", "error")
        elif not form_values["body"]:
            flash("Entry body is required.", "error")
        else:
            target_page = page
            if target_page is None:
                target_page = {
                    "id": str(uuid.uuid4()),
                    "campaign_id": campaign["id"],
                    "source": "atlas_editor",
                }
                data["wiki_pages"].append(target_page)

            target_page.update(
                {
                    "title": form_values["title"],
                    "subtitle": form_values["subtitle"],
                    "summary": form_values["summary"],
                    "image_url": form_values["image_url"],
                    "tags": form_values["tags"],
                    "related_entry_titles": form_values["related_entry_titles"],
                    "content": form_values["body"],
                    "world_category": category["key"],
                    "detail_groups": detail_groups,
                    "visibility": form_values["visibility"],
                    "visible_user_ids": sorted(selected_user_ids) if form_values["visibility"] == "selected_players" else [],
                    "status": status,
                    "updated_at": now_iso(),
                }
            )
            if "created_at" not in target_page:
                target_page["created_at"] = now_iso()

            save_data(data)
            flash("World Atlas entry published." if status == "published" else "World Atlas draft saved.", "success")
            return redirect(url_for("world_entry", page_id=target_page["id"]))

    return render_template(
        "world_editor.html",
        campaign=campaign,
        category=category,
        page=page,
        form_values=form_values,
        player_targets=player_targets,
        selected_visible_user_ids=selected_user_ids,
        visibility_options=visibility_options,
    )


@app.route("/campaigns/switch", methods=["POST"])
def switch_campaign():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    campaign_id = request.form.get("campaign_id", "").strip()

    if g.user["role"] == "dm":
        allowed = any(campaign["id"] == campaign_id for campaign in get_dm_campaigns(data, g.user["id"]))
        redirect_target = url_for("dm_dashboard")
    else:
        allowed = any(membership["campaign_id"] == campaign_id for membership in get_player_memberships(data, g.user["id"]))
        redirect_target = url_for("player_home")

    if allowed:
        session["active_campaign_id"] = campaign_id
        flash("Active campaign switched.", "success")
    else:
        flash("You do not have access to that campaign.", "error")

    return redirect(redirect_target)


@app.route("/dm/campaign", methods=["GET", "POST"])
def dm_dashboard():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "dm":
        return redirect(url_for("player_home"))

    data = load_data()
    campaign = get_active_dm_campaign(data, g.user["id"])

    if request.method == "POST":
        form_type = request.form.get("form_type", "campaign")
        campaign_name = request.form.get("campaign_name", "").strip()
        premise = request.form.get("premise", "").strip()

        if form_type == "campaign":
            if not campaign_name:
                flash("Campaign name is required.", "error")
            else:
                new_campaign = {
                    "id": str(uuid.uuid4()),
                    "name": campaign_name,
                    "premise": premise,
                    "invite_code": generate_invite_code(),
                    "dm_user_id": g.user["id"],
                }
                data["campaigns"].append(new_campaign)
                save_data(data)
                session["active_campaign_id"] = new_campaign["id"]
                flash("Campaign created. You can now share the invite code with players.", "success")
                return redirect(url_for("dm_dashboard"))
        elif campaign:
            if form_type == "premise":
                campaign["premise"] = premise
                save_data(data)
                flash("Campaign premise updated.", "success")
                return redirect(url_for("dm_dashboard"))
            if form_type == "announcement":
                broadcast_id = request.form.get("broadcast_id", "").strip()
                title = request.form.get("title", "").strip()
                body = request.form.get("body", "").strip()
                kind = request.form.get("kind", "").strip() or "Announcement"
                audience_all = request.form.get("audience_all", "").strip() == "true"
                target_user_ids = [value for value in request.form.getlist("target_user_ids") if value.strip()]
                wiki_page_id = request.form.get("wiki_page_id", "").strip() or None
                auto_create_wiki = request.form.get("auto_create_wiki", "").strip() == "true"
                world_category = request.form.get("world_category", "").strip()
                allowed_world_categories = {item["key"] for item in get_world_category_options()}
                if world_category not in allowed_world_categories:
                    world_category = ""
                if not title or not body:
                    flash("Announcement title and body are required.", "error")
                else:
                    existing_broadcast = next(
                        (
                            item
                            for item in data["announcements"]
                            if item["id"] == broadcast_id
                            and item["campaign_id"] == campaign["id"]
                            and item["author_user_id"] == g.user["id"]
                        ),
                        None,
                    )
                    if kind not in {"Hand Out", "Lore"}:
                        target_user_ids = []
                    elif audience_all:
                        target_user_ids = []

                    if kind == "Lore":
                        if wiki_page_id:
                            page = get_wiki_page_by_id(data, wiki_page_id)
                        else:
                            page = None
                        if page is None and auto_create_wiki:
                            page = {
                                "id": str(uuid.uuid4()),
                                "campaign_id": campaign["id"],
                                "title": title,
                                "content": body,
                                "source": "dm_broadcast",
                                "world_category": world_category,
                            }
                            data["wiki_pages"].append(page)
                            wiki_page_id = page["id"]
                        elif page is not None:
                            page["title"] = title
                            page["content"] = body
                            if world_category:
                                page["world_category"] = world_category
                            wiki_page_id = page["id"]
                    elif kind == "Quest":
                        if existing_broadcast and existing_broadcast.get("wiki_page_id"):
                            page = get_wiki_page_by_id(data, existing_broadcast["wiki_page_id"])
                            if page is not None:
                                page["title"] = title
                                page["content"] = body
                                wiki_page_id = page["id"]
                            else:
                                page = {
                                    "id": str(uuid.uuid4()),
                                    "campaign_id": campaign["id"],
                                    "title": title,
                                    "content": body,
                                    "source": "quest_broadcast",
                                    "world_category": "misc",
                                }
                                data["wiki_pages"].append(page)
                                wiki_page_id = page["id"]
                        else:
                            page = {
                                "id": str(uuid.uuid4()),
                                "campaign_id": campaign["id"],
                                "title": title,
                                "content": body,
                                "source": "quest_broadcast",
                                "world_category": "misc",
                            }
                            data["wiki_pages"].append(page)
                            wiki_page_id = page["id"]

                    if existing_broadcast is not None:
                        existing_broadcast["title"] = title
                        existing_broadcast["body"] = body
                        existing_broadcast["kind"] = kind
                        existing_broadcast["target_user_ids"] = target_user_ids
                        existing_broadcast["target_user_id"] = target_user_ids[0] if len(target_user_ids) == 1 else None
                        existing_broadcast["wiki_page_id"] = wiki_page_id
                        existing_broadcast["world_category"] = world_category if kind == "Lore" else ""
                    else:
                        data["announcements"].append(
                            {
                                "id": str(uuid.uuid4()),
                                "campaign_id": campaign["id"],
                                "author_user_id": g.user["id"],
                                "title": title,
                                "body": body,
                                "kind": kind,
                                "target_user_ids": target_user_ids,
                                "target_user_id": target_user_ids[0] if len(target_user_ids) == 1 else None,
                                "wiki_page_id": wiki_page_id,
                                "world_category": world_category if kind == "Lore" else "",
                                "created_at": now_iso(),
                            }
                        )
                    save_data(data)
                    flash(f"{kind} {'updated' if existing_broadcast is not None else 'posted'} for the campaign.", "success")
                    return redirect(url_for("dm_dashboard"))
            elif form_type == "note":
                title = request.form.get("title", "").strip()
                body = request.form.get("body", "").strip()
                visibility = request.form.get("visibility", "private").strip() or "private"
                if visibility not in {"private", "dm_only", "shared"}:
                    visibility = "private"
                if not title or not body:
                    flash("Note title and body are required.", "error")
                else:
                    data["notes"].append(
                        {
                            "id": str(uuid.uuid4()),
                            "campaign_id": campaign["id"],
                            "author_user_id": g.user["id"],
                            "author_name": g.user["display_name"],
                            "title": title,
                            "body": body,
                            "visibility": visibility,
                            "created_at": now_iso(),
                        }
                    )
                    save_data(data)
                    flash("Session note shared with the campaign.", "success")
                    return redirect(url_for("dm_dashboard"))

    fresh = load_data()
    campaign = get_active_dm_campaign(fresh, g.user["id"])
    all_campaigns = get_dm_campaigns(fresh, g.user["id"])
    members: list[dict[str, Any]] = []
    survey_rows: list[dict[str, Any]] = []
    announcements: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    campaign_feed: list[dict[str, Any]] = []
    wiki_pages: list[dict[str, Any]] = []
    player_targets: list[dict[str, Any]] = []
    quests: list[dict[str, Any]] = []
    quest_rows: list[dict[str, Any]] = []
    party_rows: list[dict[str, Any]] = []

    if campaign:
        members = [item for item in fresh["memberships"] if item["campaign_id"] == campaign["id"]]
        for membership in members:
            member_user = get_user_by_id(fresh, membership["user_id"])
            survey = next(
                (
                    item
                    for item in fresh["surveys"]
                    if item["campaign_id"] == campaign["id"] and item["user_id"] == membership["user_id"]
                ),
                None,
            )
            survey_rows.append(
                {
                    "display_name": member_user["display_name"] if member_user else "Unknown Player",
                    "character_name": membership["character_name"],
                    "completed": survey is not None,
                    "survey": survey,
                }
            )
            party_rows.append(
                {
                    "portrait_url": membership.get("portrait_url", "").strip(),
                    "character_name": membership.get("character_name", "Unknown Character"),
                    "class_name": membership.get("class_name") or "Class Pending",
                    "subclass": membership.get("subclass") or "Subclass Pending",
                    "armor_class": membership.get("armor_class") or "—",
                    "speed": membership.get("speed") or "—",
                    "passive_perception": membership.get("passive_perception") or "—",
                    "passive_investigation": membership.get("passive_investigation") or "—",
                    "passive_insight": membership.get("passive_insight") or "—",
                    "initiative_bonus": membership.get("initiative_bonus") or "—",
                    "proficiency_bonus": membership.get("proficiency_bonus") or "—",
                    "wiki_page_id": membership.get("wiki_page_id"),
                }
            )
        announcements = list(reversed(get_campaign_announcements(fresh, campaign["id"])))
        notes = list(reversed(get_visible_notes_for_dm(fresh, campaign["id"], g.user["id"])))
        campaign_feed = build_campaign_feed_items(fresh, campaign["id"], include_all_notes=True)
        wiki_pages = get_campaign_wiki_pages(fresh, campaign["id"])
        quests = list(reversed(get_campaign_quests(fresh, campaign["id"])))
        acceptance_lookup: dict[str, list[str]] = {}
        for acceptance in fresh["quest_acceptances"]:
            if acceptance["campaign_id"] != campaign["id"]:
                continue
            acceptance_lookup.setdefault(acceptance["quest_id"], []).append(acceptance["user_id"])
        player_targets = [
            {
                "user_id": membership["user_id"],
                "character_name": membership["character_name"],
                "display_name": get_user_by_id(fresh, membership["user_id"])["display_name"]
                if get_user_by_id(fresh, membership["user_id"])
                else "Unknown Player",
            }
            for membership in members
        ]
        player_name_lookup = {
            item["user_id"]: f"{item['display_name']} · {item['character_name']}"
            for item in player_targets
        }
        for quest in quests:
            accepted_user_ids = acceptance_lookup.get(quest["id"], [])
            quest_rows.append(
                {
                    "id": quest["id"],
                    "title": quest["title"],
                    "body": quest["body"],
                    "author_user_id": quest.get("author_user_id"),
                    "wiki_page_id": quest.get("wiki_page_id"),
                    "target_user_ids": quest.get("target_user_ids") or ([] if not quest.get("target_user_id") else [quest["target_user_id"]]),
                    "accepted_count": len(accepted_user_ids),
                    "accepted_names": [player_name_lookup[user_id] for user_id in accepted_user_ids if user_id in player_name_lookup],
                    "is_accepted": bool(accepted_user_ids),
                    "rendered_body": render_wiki_markup(quest.get("body", ""), fresh, campaign["id"]),
                }
            )

    return render_template(
        "dm_dashboard.html",
        campaign=campaign,
        all_campaigns=all_campaigns,
        survey_rows=survey_rows,
        members=members,
        announcements=announcements,
        notes=notes,
        campaign_feed=campaign_feed,
        wiki_pages=wiki_pages,
        world_category_options=get_world_category_options(),
        player_targets=player_targets,
        quests=quests,
        quest_rows=quest_rows,
        party_rows=party_rows,
    )


@app.route("/player/home")
def player_home():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        return redirect(url_for("join_campaign"))

    campaign = get_campaign_by_id(data, membership["campaign_id"])
    announcements = [
        {
            **item,
            "rendered_body": render_wiki_markup(item.get("body", ""), data, membership["campaign_id"]),
        }
        for item in reversed(get_visible_broadcasts_for_player(data, membership["campaign_id"], g.user["id"]))
    ]
    notes = list(reversed(get_visible_notes_for_player(data, membership["campaign_id"], g.user["id"])))
    campaign_feed = build_campaign_feed_items(data, membership["campaign_id"], user_id=g.user["id"])
    quests = list(reversed(get_campaign_quests(data, membership["campaign_id"])))
    wiki_pages = get_campaign_wiki_pages(data, membership["campaign_id"])
    accepted_quest_ids = {
        acceptance["quest_id"]
        for acceptance in data["quest_acceptances"]
        if acceptance["user_id"] == g.user["id"]
    }
    survey = next(
        (
            item
            for item in data["surveys"]
            if item["campaign_id"] == membership["campaign_id"] and item["user_id"] == g.user["id"]
        ),
        None,
    )
    if survey is None:
        return redirect(url_for("player_onboarding", campaign_id=membership["campaign_id"]))

    visible_nonquest_broadcasts = [item for item in announcements if item.get("kind") != "Quest"]
    open_quests = [item for item in quests if item["id"] not in accepted_quest_ids]
    party_snapshot = []
    for other_membership in data["memberships"]:
        if other_membership["campaign_id"] != membership["campaign_id"] or other_membership["user_id"] == g.user["id"]:
            continue
        party_snapshot.append(
            {
                "membership_id": other_membership["id"],
                "portrait_url": other_membership.get("portrait_url", "").strip(),
                "character_name": other_membership.get("character_name", "Unknown Character"),
                "class_name": other_membership.get("class_name") or "Class Pending",
                "subclass": other_membership.get("subclass") or "Subclass Pending",
            }
        )

    if not has_completed_character_sheet(membership):
        next_step = {
            "title": "Complete your character sheet",
            "detail": "Finish your stats and character details before the next session.",
            "href": url_for("player_character_sheet", campaign_id=membership["campaign_id"]),
            "label": "Open Character Sheet",
        }
    elif open_quests:
        next_step = {
            "title": "Choose your next quest",
            "detail": f"{len(open_quests)} quest{'s' if len(open_quests) != 1 else ''} are still open on the board.",
            "href": url_for("player_home"),
            "label": "Review Quest Board",
        }
    elif visible_nonquest_broadcasts:
        next_step = {
            "title": "Review the latest DM updates",
            "detail": f"{len(visible_nonquest_broadcasts)} recent broadcast{'s' if len(visible_nonquest_broadcasts) != 1 else ''} are available to read.",
            "href": url_for("player_home"),
            "label": "Open Campaign Feed",
        }
    else:
        next_step = {
            "title": "Keep your notes current",
            "detail": "Use your notes drawer to capture clues, NPC names, and unresolved threads.",
            "href": url_for("player_home"),
            "label": "Go To Dashboard",
        }

    now_next = {
        "next_session": "Awaiting DM schedule",
        "update_count": len(visible_nonquest_broadcasts),
        "open_quests": len(open_quests),
        "accepted_quests": len(accepted_quest_ids),
        "character_sheet_complete": has_completed_character_sheet(membership),
        "next_step": next_step,
    }

    return render_template(
        "player_home.html",
        campaign=campaign,
        membership=membership,
        survey=survey,
        announcements=announcements,
        notes=notes,
        campaign_feed=campaign_feed,
        character_notes=list(reversed(get_character_notes(data, membership["campaign_id"], g.user["id"]))),
        quests=quests,
        wiki_pages=wiki_pages,
        accepted_quest_ids=accepted_quest_ids,
        all_memberships=get_player_memberships(data, g.user["id"]),
        now_next=now_next,
        party_snapshot=party_snapshot,
        ability_cells=build_ability_cells(membership),
        notable_proficiencies=build_summary_notable_proficiencies(membership.get("notable_proficiencies")),
    )


@app.route("/player/character-sheet", methods=["GET", "POST"])
def player_character_sheet():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    requested_campaign_id = request.args.get("campaign_id", "").strip()
    if requested_campaign_id:
        membership = get_membership(data, requested_campaign_id, g.user["id"])
        if membership is not None:
            session["active_campaign_id"] = membership["campaign_id"]
    else:
        membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        flash("Join a campaign before opening a character sheet.", "error")
        return redirect(url_for("campaigns_page"))

    campaign = get_campaign_by_id(data, membership["campaign_id"])
    if not has_completed_onboarding(data, membership["campaign_id"], g.user["id"]):
        flash("Complete onboarding before creating your character sheet.", "error")
        return redirect(url_for("campaigns_page", campaign_id=membership["campaign_id"]))

    if request.method == "POST":
        fields = (
            "portrait_url",
            "class_name",
            "subclass",
            "level",
            "species",
            "background",
            "alignment",
            "armor_class",
            "speed",
            "max_hit_points",
            "current_hit_points",
            "temp_hit_points",
            "initiative_bonus",
            "proficiency_bonus",
            "passive_perception",
            "passive_investigation",
            "passive_insight",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
            "character_notes",
            "notable_proficiencies",
        )
        for field in fields:
            membership[field] = request.form.get(field, "").strip()

        membership["death_save_successes"] = str(parse_counter(request.form.get("death_save_successes", "0")))
        membership["death_save_failures"] = str(parse_counter(request.form.get("death_save_failures", "0")))

        page = get_wiki_page_by_id(data, membership.get("wiki_page_id", ""))
        if page is None:
            page = {
                "id": str(uuid.uuid4()),
                "campaign_id": membership["campaign_id"],
                "title": membership["character_name"],
                "content": build_character_wiki_content(membership),
                "source": "character_profile",
                "membership_id": membership["id"],
            }
            membership["wiki_page_id"] = page["id"]
            data["wiki_pages"].append(page)
        else:
            page["title"] = membership["character_name"]
            page["content"] = build_character_wiki_content(membership)

        save_data(data)
        flash("Character sheet saved.", "success")
        return redirect(url_for("player_character_sheet"))

    return render_template(
        "character_sheet.html",
        campaign=campaign,
        membership=membership,
        ability_cells=build_ability_cells(membership),
        notable_proficiencies=parse_notable_proficiencies(membership.get("notable_proficiencies")),
        death_save_successes=parse_counter(membership.get("death_save_successes", "0")),
        death_save_failures=parse_counter(membership.get("death_save_failures", "0")),
    )


@app.route("/character/<membership_id>")
def character_page(membership_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    membership = get_membership_by_id(data, membership_id)
    if membership is None or not user_can_access_campaign(data, g.user, membership["campaign_id"]):
        flash("That character page is not available to your account.", "error")
        return redirect(url_for("home"))

    campaign = get_campaign_by_id(data, membership["campaign_id"])
    character_user = get_user_by_id(data, membership["user_id"])
    character_notes = list(reversed(get_character_notes(data, membership["campaign_id"], membership["user_id"])))
    rendered_character_notes = [
        {
            **item,
            "rendered_body": render_wiki_markup(item.get("body", ""), data, membership["campaign_id"]),
        }
        for item in character_notes
    ]
    return render_template(
        "character_page.html",
        campaign=campaign,
        membership=membership,
        character_user=character_user,
        character_notes=rendered_character_notes,
    )


@app.route("/character/<membership_id>/sheet")
def character_sheet_alt(membership_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    membership = get_membership_by_id(data, membership_id)
    if membership is None or not user_can_access_campaign(data, g.user, membership["campaign_id"]):
        flash("That character sheet is not available to your account.", "error")
        return redirect(url_for("home"))

    campaign = get_campaign_by_id(data, membership["campaign_id"])
    character_user = get_user_by_id(data, membership["user_id"])
    survey = next(
        (
            item
            for item in data["surveys"]
            if item["campaign_id"] == membership["campaign_id"] and item["user_id"] == membership["user_id"]
        ),
        None,
    )
    can_manage = g.user["role"] == "dm" or g.user["id"] == membership["user_id"]
    can_edit_sheet = g.user["role"] == "player" and g.user["id"] == membership["user_id"]
    all_character_notes = list(reversed(get_character_notes(data, membership["campaign_id"], membership["user_id"])))
    visible_character_notes = (
        all_character_notes
        if can_manage
        else [item for item in all_character_notes if item.get("visibility", "private") == "shared"]
    )
    rendered_character_notes = [
        {
            **item,
            "rendered_body": render_wiki_markup(item.get("body", ""), data, membership["campaign_id"]),
        }
        for item in visible_character_notes
    ]
    quick_actions = [
        {"name": "Attack", "detail": "Make one weapon or spell attack."},
        {"name": "Dash", "detail": "Gain extra movement this turn."},
        {"name": "Disengage", "detail": "Move without provoking opportunity attacks."},
        {"name": "Dodge", "detail": "Attackers have disadvantage until your next turn."},
        {"name": "Help", "detail": "Grant advantage to an ally or aid a task."},
        {"name": "Hide", "detail": "Attempt to become unseen."},
        {"name": "Ready", "detail": "Prepare an action for a trigger."},
        {"name": "Search", "detail": "Look for hidden threats or clues."},
        {"name": "Use an Object", "detail": "Interact with gear beyond the free object interaction."},
    ]
    return render_template(
        "character_page_alt.html",
        campaign=campaign,
        membership=membership,
        character_user=character_user,
        survey=survey,
        can_manage=can_manage,
        can_edit_sheet=can_edit_sheet,
        ability_cells=build_ability_cells(membership),
        notable_proficiencies=build_summary_notable_proficiencies(membership.get("notable_proficiencies")),
        death_save_successes=parse_counter(membership.get("death_save_successes", "0")),
        death_save_failures=parse_counter(membership.get("death_save_failures", "0")),
        character_notes=rendered_character_notes,
        quick_actions=quick_actions,
        rendered_story_hook=render_wiki_markup(
            survey.story_hook if survey and survey.story_hook else membership.character_notes or "No character hook has been written yet.",
            data,
            membership["campaign_id"],
        ),
        rendered_character_notes_text=render_wiki_markup(
            membership.character_notes or "No character notes have been added yet.",
            data,
            membership["campaign_id"],
        ),
        rendered_dream_campaign=render_wiki_markup(
            survey.raw_responses.dream_campaign if survey and survey.raw_responses and survey.raw_responses.dream_campaign else "No dream campaign note has been added yet.",
            data,
            membership["campaign_id"],
        ),
        rendered_expectation_notes=render_wiki_markup(
            survey.raw_responses.expectation_notes if survey and survey.raw_responses and survey.raw_responses.expectation_notes else "No extra campaign expectations have been shared yet.",
            data,
            membership["campaign_id"],
        ),
        rendered_player_spotlight=render_wiki_markup(
            survey.raw_responses.player_note if survey and survey.raw_responses and survey.raw_responses.player_note else "No player preference note has been added yet.",
            data,
            membership["campaign_id"],
        ),
    )


@app.route("/character/<membership_id>/codex")
def character_codex(membership_id: str):
    return redirect(url_for("character_world_entry", membership_id=membership_id))


@app.route("/character/<membership_id>/world")
def character_world_entry(membership_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    membership = get_membership_by_id(data, membership_id)
    if membership is None or not user_can_access_campaign(data, g.user, membership["campaign_id"]):
        flash("That character world entry is not available to your account.", "error")
        return redirect(url_for("home"))

    page = get_wiki_page_by_id(data, membership.get("wiki_page_id", ""))
    if page is None:
        flash("This character does not have a world entry yet.", "error")
        return redirect(url_for("character_page", membership_id=membership_id))
    if not can_user_view_world_page(data, g.user, page):
        flash("That character world entry is not available to your account.", "error")
        return redirect(url_for("character_page", membership_id=membership_id))

    campaign = get_campaign_by_id(data, membership["campaign_id"])
    character_user = get_user_by_id(data, membership["user_id"])
    related_pages = build_related_wiki_pages(data, membership["campaign_id"], page["id"], user=g.user)
    visible_names = get_world_page_visible_names(data, membership["campaign_id"], page.get("visible_user_ids", []))
    return render_template(
        "world_entry.html",
        campaign=campaign,
        page=page,
        rendered_content=render_wiki_markup(page.get("content", ""), data, membership["campaign_id"]),
        related_pages=related_pages,
        visible_names=visible_names,
        membership=membership,
        character_user=character_user,
        is_character_codex=True,
    )


@app.route("/wiki/<page_id>")
def wiki_page(page_id: str):
    return redirect(url_for("world_entry", page_id=page_id))


@app.route("/world/<page_id>")
def world_entry(page_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    page = get_wiki_page_by_id(data, page_id)
    if page is None or not can_user_view_world_page(data, g.user, page):
        flash("That world entry is not available to your account.", "error")
        return redirect(url_for("home"))

    campaign = get_campaign_by_id(data, page["campaign_id"])
    membership = get_membership_by_id(data, page.get("membership_id", "")) if page.get("membership_id") else None
    character_user = get_user_by_id(data, membership["user_id"]) if membership else None
    related_pages = build_related_wiki_pages(data, page["campaign_id"], page["id"], user=g.user)
    visible_names = get_world_page_visible_names(data, page["campaign_id"], page.get("visible_user_ids", []))
    is_character_codex = membership is not None
    return render_template(
        "world_entry.html",
        campaign=campaign,
        page=page,
        rendered_content=render_wiki_markup(page.get("content", ""), data, page["campaign_id"]),
        related_pages=related_pages,
        visible_names=visible_names,
        membership=membership,
        character_user=character_user,
        is_character_codex=is_character_codex,
    )


@app.route("/wiki/<page_id>/codex")
def wiki_page_codex(page_id: str):
    return redirect(url_for("world_entry", page_id=page_id))


@app.route("/player/join", methods=["GET", "POST"])
def join_campaign():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()

    if request.method == "POST":
        invite_code = request.form.get("invite_code", "").strip()
        character_name = request.form.get("character_name", "").strip()
        campaign = get_campaign_by_invite(data, invite_code)

        if campaign is None:
            flash("That invite code was not recognized.", "error")
        elif not character_name:
            flash("Character name is required before joining.", "error")
        elif get_membership(data, campaign["id"], g.user["id"]):
            session["active_campaign_id"] = campaign["id"]
            flash(f"You are already in {campaign['name']}. Switched to that campaign instead.", "success")
            return redirect(url_for("campaigns_page", campaign_id=campaign["id"]))
        else:
            membership_id = str(uuid.uuid4())
            membership = {
                "id": membership_id,
                "campaign_id": campaign["id"],
                "user_id": g.user["id"],
                "character_name": character_name,
                "portrait_url": "",
                "class_name": "",
                "subclass": "",
                "level": "",
                "species": "",
                "background": "",
                "alignment": "",
                "armor_class": "",
                "speed": "",
                "max_hit_points": "",
                "current_hit_points": "",
                "temp_hit_points": "",
                "passive_perception": "",
                "passive_investigation": "",
                "passive_insight": "",
                "initiative_bonus": "",
                "proficiency_bonus": "",
                "strength": "",
                "dexterity": "",
                "constitution": "",
                "intelligence": "",
                "wisdom": "",
                "charisma": "",
                "character_notes": "",
                "notable_proficiencies": "",
                "death_save_successes": "0",
                "death_save_failures": "0",
            }
            character_wiki_page = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign["id"],
                "title": character_name,
                "content": build_character_wiki_content(membership),
                "source": "character_profile",
                "membership_id": membership_id,
            }
            membership["wiki_page_id"] = character_wiki_page["id"]
            data["memberships"].append(
                membership
            )
            data["wiki_pages"].append(character_wiki_page)
            save_data(data)
            session["active_campaign_id"] = campaign["id"]
            flash(f"You joined {campaign['name']}. Complete onboarding before creating your character sheet.", "success")
            return redirect(url_for("campaigns_page", campaign_id=campaign["id"]))

    return render_template("join_campaign.html")


@app.route("/player/onboarding/<campaign_id>", methods=["GET", "POST"])
def player_onboarding(campaign_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    campaign = get_campaign_by_id(data, campaign_id)
    membership = get_membership(data, campaign_id, g.user["id"])
    if campaign is None or membership is None:
        flash("Join a campaign before filling out the onboarding survey.", "error")
        return redirect(url_for("join_campaign"))

    existing = next(
        (
            item
            for item in data["surveys"]
            if item["campaign_id"] == campaign_id and item["user_id"] == g.user["id"]
        ),
        None,
    )
    if existing:
        return redirect(url_for("player_home"))

    if request.method == "POST":
        selected_genres = request.form.getlist("genres")
        selected_expectations = request.form.getlist("expectations")
        line_items = request.form.getlist("line_items")
        veil_items = request.form.getlist("veil_items")
        tone_focus = request.form.get("tone_notes", "").strip()
        dream_campaign = request.form.get("dream_campaign", "").strip()
        logistics_summary = ", ".join(
            item
            for item in [
                request.form.get("timezone", "").strip(),
                request.form.get("session_length", "").strip(),
                request.form.get("frequency", "").strip(),
                request.form.get("best_days", "").strip(),
                request.form.get("hard_stop", "").strip(),
            ]
            if item
        )
        play_style_summary = ", ".join(
            item
            for item in [
                request.form.get("experience_level", "").strip(),
                request.form.get("play_format", "").strip(),
                request.form.get("favorite_parts", "").strip(),
            ]
            if item
        )
        boundaries_parts = []
        if line_items:
            boundaries_parts.append("Lines: " + ", ".join(line_items))
        if veil_items:
            boundaries_parts.append("Veils: " + ", ".join(veil_items))
        if request.form.get("custom_line", "").strip():
            boundaries_parts.append("Custom line: " + request.form.get("custom_line", "").strip())
        if request.form.get("custom_veil", "").strip():
            boundaries_parts.append("Custom veil: " + request.form.get("custom_veil", "").strip())
        if request.form.get("boundary_notes", "").strip():
            boundaries_parts.append(request.form.get("boundary_notes", "").strip())

        survey = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "user_id": g.user["id"],
            "play_style": play_style_summary or request.form.get("play_style", "").strip(),
            "tone": " | ".join(
                item
                for item in [
                    ", ".join(selected_genres) if selected_genres else "",
                    tone_focus,
                    dream_campaign,
                ]
                if item
            ),
            "schedule_notes": " | ".join(
                item
                for item in [logistics_summary, request.form.get("schedule_notes", "").strip()]
                if item
            ),
            "boundaries": " | ".join(boundaries_parts),
            "story_hook": request.form.get("story_hook", "").strip(),
            "raw_responses": {
                "player_name": request.form.get("player_name", "").strip(),
                "discord_handle": request.form.get("discord_handle", "").strip(),
                "experience_level": request.form.get("experience_level", "").strip(),
                "favorite_parts": request.form.get("favorite_parts", "").strip(),
                "timezone": request.form.get("timezone", "").strip(),
                "session_length": request.form.get("session_length", "").strip(),
                "frequency": request.form.get("frequency", "").strip(),
                "best_days": request.form.get("best_days", "").strip(),
                "hard_stop": request.form.get("hard_stop", "").strip(),
                "attendance": request.form.get("attendance", "").strip(),
                "schedule_notes": request.form.get("schedule_notes", "").strip(),
                "play_format": request.form.get("play_format", "").strip(),
                "genres": selected_genres,
                "genre_details": request.form.get("genre_details", "").strip(),
                "tone_notes": tone_focus,
                "line_items": line_items,
                "veil_items": veil_items,
                "custom_line": request.form.get("custom_line", "").strip(),
                "custom_veil": request.form.get("custom_veil", "").strip(),
                "boundary_notes": request.form.get("boundary_notes", "").strip(),
                "expectations": selected_expectations,
                "expectation_notes": request.form.get("expectation_notes", "").strip(),
                "dream_campaign": dream_campaign,
                "story_hook": request.form.get("story_hook", "").strip(),
            },
        }
        if not all(survey[key] for key in ("play_style", "tone", "boundaries", "story_hook")):
            flash("Please complete the required survey fields.", "error")
        else:
            data["surveys"].append(survey)
            save_data(data)
            flash("Your onboarding survey has been shared with the DM.", "success")
            return redirect(url_for("player_character_sheet", campaign_id=membership["campaign_id"]))

    return render_template("onboarding.html", campaign=campaign, membership=membership)


@app.route("/player/notes", methods=["POST"])
def player_note():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        return redirect(url_for("join_campaign"))

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    note_id = request.form.get("note_id", "").strip()
    visibility = request.form.get("visibility", "private").strip() or "private"
    if visibility not in {"private", "dm_only", "shared"}:
        visibility = "private"
    if not title or not body:
        flash("Shared note title and body are required.", "error")
    else:
        existing_note = next(
            (
                item
                for item in data["notes"]
                if item["id"] == note_id
                and item["campaign_id"] == membership["campaign_id"]
                and item["author_user_id"] == g.user["id"]
            ),
            None,
        )
        if existing_note is not None:
            existing_note["title"] = title
            existing_note["body"] = body
            existing_note["visibility"] = visibility
        else:
            data["notes"].append(
                {
                    "id": str(uuid.uuid4()),
                    "campaign_id": membership["campaign_id"],
                    "author_user_id": g.user["id"],
                    "author_name": g.user["display_name"],
                    "title": title,
                    "body": body,
                    "visibility": visibility,
                    "created_at": now_iso(),
                }
            )
        save_data(data)
        flash("Your note has been saved.", "success")

    referrer = request.form.get("next") or request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for("player_home"))


@app.route("/player/death-saves", methods=["POST"])
def player_death_saves():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        return redirect(url_for("join_campaign"))

    membership["death_save_successes"] = str(parse_counter(request.form.get("death_save_successes", "0")))
    membership["death_save_failures"] = str(parse_counter(request.form.get("death_save_failures", "0")))
    save_data(data)

    if is_fetch_request():
        return jsonify(
            {
                "ok": True,
                "death_save_successes": membership["death_save_successes"],
                "death_save_failures": membership["death_save_failures"],
            }
        )
    return redirect(url_for("player_home"))


@app.route("/player/notes/<note_id>/delete", methods=["POST"])
def delete_player_note(note_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        return redirect(url_for("join_campaign"))

    note = next(
        (
            item
            for item in data["notes"]
            if item["id"] == note_id
            and item["campaign_id"] == membership["campaign_id"]
            and item["author_user_id"] == g.user["id"]
        ),
        None,
    )

    if note is None:
        flash("That note could not be found or does not belong to you.", "error")
        return redirect(request.form.get("next") or request.referrer or url_for("player_home"))

    data["notes"] = [item for item in data["notes"] if item["id"] != note_id]
    save_data(data)
    flash("Your note has been deleted.", "success")
    return redirect(request.form.get("next") or request.referrer or url_for("player_home"))


@app.route("/dm/broadcasts/<broadcast_id>/delete", methods=["POST"])
def delete_dm_broadcast(broadcast_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "dm":
        return redirect(url_for("player_home"))

    data = load_data()
    campaign = get_active_dm_campaign(data, g.user["id"])
    if campaign is None:
        return redirect(url_for("dm_dashboard"))

    broadcast = next(
        (
            item
            for item in data["announcements"]
            if item["id"] == broadcast_id
            and item["campaign_id"] == campaign["id"]
            and item["author_user_id"] == g.user["id"]
        ),
        None,
    )
    if broadcast is None:
        flash("That broadcast could not be found or does not belong to you.", "error")
        return redirect(request.form.get("next") or request.referrer or url_for("dm_dashboard"))

    data["announcements"] = [item for item in data["announcements"] if item["id"] != broadcast_id]
    save_data(data)
    flash("Broadcast deleted.", "success")
    return redirect(request.form.get("next") or request.referrer or url_for("dm_dashboard"))


@app.route("/player/broadcasts/<broadcast_id>/add-to-notes", methods=["POST"])
def add_broadcast_to_notes(broadcast_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    broadcast = get_broadcast_by_id(data, broadcast_id)
    if membership is None or broadcast is None or broadcast["campaign_id"] != membership["campaign_id"]:
        if is_fetch_request():
            return jsonify({"ok": False, "message": "That broadcast is not available in your active campaign."}), 404
        flash("That broadcast is not available in your active campaign.", "error")
        return redirect(url_for("player_home"))

    targets = broadcast.get("target_user_ids") or []
    legacy_target = broadcast.get("target_user_id")
    if legacy_target and not targets:
        targets = [legacy_target]

    if targets and g.user["id"] not in targets:
        if is_fetch_request():
            return jsonify({"ok": False, "message": "That handout is not available to your account."}), 403
        flash("That handout is not available to your account.", "error")
        return redirect(url_for("player_home"))

    data["notes"].append(
        {
            "id": str(uuid.uuid4()),
            "campaign_id": membership["campaign_id"],
            "author_user_id": g.user["id"],
            "author_name": g.user["display_name"],
            "title": f"{broadcast['kind']}: {broadcast['title']}",
            "body": broadcast["body"],
            "visibility": "private",
            "created_at": now_iso(),
        }
    )
    save_data(data)
    if is_fetch_request():
        return jsonify({"ok": True, "message": f"{broadcast['kind']} added to your session notes."})
    flash(f"{broadcast['kind']} added to your session notes.", "success")
    return redirect(url_for("player_home"))


@app.route("/player/feed")
def player_feed():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return jsonify({"error": "forbidden"}), 403

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        return jsonify({"broadcasts": [], "notes": [], "campaign_feed": [], "accepted_quest_ids": []})

    broadcasts = list(reversed(get_visible_broadcasts_for_player(data, membership["campaign_id"], g.user["id"])))
    notes = list(reversed(get_visible_notes_for_player(data, membership["campaign_id"], g.user["id"])))
    campaign_feed = build_campaign_feed_items(data, membership["campaign_id"], user_id=g.user["id"])
    accepted_quest_ids = [
        acceptance["quest_id"]
        for acceptance in data["quest_acceptances"]
        if acceptance["user_id"] == g.user["id"] and acceptance["campaign_id"] == membership["campaign_id"]
    ]

    return jsonify(
        {
            "broadcasts": broadcasts,
            "notes": notes,
            "campaign_feed": campaign_feed,
            "accepted_quest_ids": accepted_quest_ids,
        }
    )


@app.route("/player/quests/<quest_id>/accept", methods=["POST"])
def accept_quest(quest_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    if membership is None:
        if is_fetch_request():
            return jsonify({"ok": False, "message": "Join a campaign before accepting quests."}), 404
        return redirect(url_for("join_campaign"))

    quest = next((item for item in data["announcements"] if item["id"] == quest_id and item.get("kind") == "Quest"), None)
    if quest is None or quest["campaign_id"] != membership["campaign_id"]:
        if is_fetch_request():
            return jsonify({"ok": False, "message": "That quest is not available in your active campaign."}), 404
        flash("That quest is not available in your active campaign.", "error")
        return redirect(url_for("player_home"))

    existing = get_quest_acceptance(data, quest_id, g.user["id"])
    if existing is None:
        data["quest_acceptances"].append(
            {
                "id": str(uuid.uuid4()),
                "quest_id": quest_id,
                "user_id": g.user["id"],
                "campaign_id": membership["campaign_id"],
            }
        )
        save_data(data)
        if is_fetch_request():
            return jsonify({"ok": True, "message": "Quest accepted and pinned to your bulletin board."})
        flash("Quest accepted and pinned to your bulletin board.", "success")
    else:
        if is_fetch_request():
            return jsonify({"ok": True, "message": "You have already accepted that quest."})
        flash("You have already accepted that quest.", "success")

    return redirect(url_for("player_home"))


@app.route("/player/lore/<page_id>/add-to-notes", methods=["POST"])
def add_lore_to_notes(page_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    if g.user["role"] != "player":
        return redirect(url_for("dm_dashboard"))

    data = load_data()
    membership = get_active_player_membership(data, g.user["id"])
    page = get_wiki_page_by_id(data, page_id)
    if membership is None or page is None or page["campaign_id"] != membership["campaign_id"]:
        if is_fetch_request():
            return jsonify({"ok": False, "message": "That lore page is not available in your active campaign."}), 404
        flash("That lore page is not available in your active campaign.", "error")
        return redirect(url_for("player_home"))

    data["notes"].append(
        {
            "id": str(uuid.uuid4()),
            "campaign_id": membership["campaign_id"],
            "author_user_id": g.user["id"],
            "author_name": g.user["display_name"],
            "title": f"Lore Note: {page['title']}",
            "body": page["content"],
            "visibility": "private",
            "created_at": now_iso(),
        }
    )
    save_data(data)
    if is_fetch_request():
        return jsonify({"ok": True, "message": "Lore page added to your session notes."})
    flash("Lore page added to your session notes.", "success")
    return redirect(url_for("player_home"))


if __name__ == "__main__":
    ensure_data_file()
    app.run(debug=True)
