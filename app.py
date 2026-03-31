from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
                "author_name": "Dungeon Master",
                "author_user_id": item.get("author_user_id"),
                "target_user_ids": item.get("target_user_ids") or ([] if not item.get("target_user_id") else [item["target_user_id"]]),
                "visibility": None,
                "created_at": item.get("created_at", ""),
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
            }
        )

    return sorted(feed_items, key=lambda item: item.get("created_at", ""), reverse=True)


def user_can_access_campaign(data: dict[str, list[dict[str, Any]]], user: dict[str, Any], campaign_id: str) -> bool:
    if user["role"] == "dm":
        campaign = get_campaign_by_id(data, campaign_id)
        return campaign is not None and campaign["dm_user_id"] == user["id"]
    return get_membership(data, campaign_id, user["id"]) is not None


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

    return {
        "current_user": g.user,
        "account_campaigns": account_campaigns,
        "active_sidebar_campaign": active_sidebar_campaign,
        "active_sidebar_membership": active_sidebar_membership,
        "drawer_character_notes": drawer_character_notes,
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
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    campaign = None
    if g.user["role"] == "dm":
        campaign = get_active_dm_campaign(data, g.user["id"])
    else:
        membership = get_active_player_membership(data, g.user["id"])
        if membership is not None:
            campaign = get_campaign_by_id(data, membership["campaign_id"])

    pages = get_campaign_wiki_pages(data, campaign["id"]) if campaign else []
    return render_template("wiki_index.html", pages=pages, campaign=campaign)


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
                            }
                            data["wiki_pages"].append(page)
                            wiki_page_id = page["id"]
                        elif page is not None:
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
    announcements = list(reversed(get_visible_broadcasts_for_player(data, membership["campaign_id"], g.user["id"])))
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
    return render_template(
        "character_page.html",
        campaign=campaign,
        membership=membership,
        character_user=character_user,
        character_notes=character_notes,
    )


@app.route("/wiki/<page_id>")
def wiki_page(page_id: str):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    data = load_data()
    page = get_wiki_page_by_id(data, page_id)
    if page is None or not user_can_access_campaign(data, g.user, page["campaign_id"]):
        flash("That wiki page is not available to your account.", "error")
        return redirect(url_for("home"))

    campaign = get_campaign_by_id(data, page["campaign_id"])
    return render_template("wiki_page.html", page=page, campaign=campaign)


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
