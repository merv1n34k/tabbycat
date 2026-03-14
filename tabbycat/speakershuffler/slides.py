"""Slide generator for Fight Club rounds.

Generates one PNG slide per room using template.png as background.
Each slide shows round name + room at the top, speaker photos in 8 slots,
and speaker names under each photo.
"""

import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Photo slot positions (pixel coords at 1920×1080, measured from template.png)
# ---------------------------------------------------------------------------

# Each slot: (x, y) top-left corner.  Photo size: 285×346.
# 4 teams × 2 speakers = 8 slots.
# Layout: two groups of 4, left half and right half, each 2×2.
PHOTO_SLOTS = [
    # Team 1 (top-left)
    (108, 194), (464, 194),
    # Team 2 (top-right)
    (1165, 194), (1521, 194),
    # Team 3 (bottom-left)
    (108, 626), (464, 626),
    # Team 4 (bottom-right)
    (1165, 626), (1521, 626),
]
PHOTO_W, PHOTO_H = 285, 346

NAME_GAP = 10          # pixels below photo bottom for speaker name
HEADER_Y = 97          # vertical center of header text

TEXT_COLOR = (30, 25, 10)       # dark warm brown on yellow background
TEXT_COLOR_LIGHT = (80, 65, 30) # lighter variant for secondary text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_photo(photos_dir, speaker_name):
    """Find a photo file matching the speaker name (case-insensitive)."""
    photos_path = Path(photos_dir)
    name_lower = speaker_name.lower().replace(' ', '_')
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        candidate = photos_path / f"{name_lower}{ext}"
        if candidate.exists():
            return candidate
        candidate = photos_path / f"{speaker_name}{ext}"
        if candidate.exists():
            return candidate
    # Fuzzy: match stem ignoring case
    for f in photos_path.iterdir():
        if f.stem.lower() == name_lower and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            return f
    # Try original name with spaces (for Ukrainian names etc.)
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        candidate = photos_path / f"{speaker_name}{ext}"
        if candidate.exists():
            return candidate
    return None


def _load_font(size):
    """Load a font, falling back through several options."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_room_slide(debate, round_obj, photos_dir, template_path, output_path):
    """Generate one slide for a single room/debate."""
    from draw.models import DebateTeam
    from participants.models import Speaker

    img = Image.open(template_path).convert('RGB')
    # Scale to 1920×1080 if template is a different size
    if img.size != (1920, 1080):
        img = img.resize((1920, 1080), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    font_header = _load_font(48)
    font_name = _load_font(22)

    # Header: "Round N  —  Room Name"
    room_name = debate.venue.name if debate.venue else f"Room {debate.pk}"
    header_text = f"{round_obj.name}  \u2014  {room_name}"
    draw.text((1920 // 2, HEADER_Y), header_text, fill=TEXT_COLOR,
              font=font_header, anchor="mm")

    # Get debate teams in side order
    debate_teams = list(
        DebateTeam.objects.filter(debate=debate)
        .select_related('team')
        .order_by('side'),
    )

    # Place photos and names into slots
    slot_idx = 0
    for dt in debate_teams[:4]:
        speakers = list(Speaker.objects.filter(team=dt.team).order_by('pk'))
        for speaker in speakers[:2]:
            if slot_idx >= len(PHOTO_SLOTS):
                break
            px, py = PHOTO_SLOTS[slot_idx]
            cx = px + PHOTO_W // 2

            # Paste photo
            photo_path = _find_photo(photos_dir, speaker.name)
            if photo_path:
                try:
                    photo = Image.open(photo_path).convert('RGB')
                    photo = photo.resize((PHOTO_W, PHOTO_H), Image.LANCZOS)
                    img.paste(photo, (px, py))
                except Exception as e:
                    logger.warning("Could not load photo for %s: %s", speaker.name, e)

            # Speaker name below photo
            name_y = py + PHOTO_H + NAME_GAP
            draw.text((cx, name_y), speaker.name, fill=TEXT_COLOR,
                      font=font_name, anchor="mt")

            slot_idx += 1

    # Save
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output), "PNG")
    logger.info("Generated slide: %s", output)
    return output


def generate_round_slides(round_obj, photos_dir, template_path, output_dir):
    """Generate one slide per room for a round."""
    from draw.models import Debate

    debates = (
        Debate.objects.filter(round=round_obj)
        .select_related('venue')
        .order_by('venue__name', 'pk')
    )

    if not debates:
        logger.warning("No debates found for %s", round_obj)
        return []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    slides = []
    for i, debate in enumerate(debates, 1):
        room_label = debate.venue.name if debate.venue else f"room{i}"
        filename = f"{round_obj.abbreviation}_{room_label}.png".replace(' ', '_')
        filepath = output_path / filename
        result = generate_room_slide(
            debate, round_obj, photos_dir, template_path, str(filepath),
        )
        if result:
            slides.append(result)

    return slides
