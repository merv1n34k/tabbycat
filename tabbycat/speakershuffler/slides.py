"""Slide generator for Fight Club rounds.

Generates one PNG slide per round showing all teams in BP positions
(OG, OO, CG, CO) with speaker photos. Photos are matched by speaker
name to filenames in the photos directory (e.g., speaker "cat1" -> "cat1.png").

Visual style: full-bleed noir layout with serif typography and gold accents.
"""

import logging
import os
import random as _random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dimensions — full-bleed 4-quadrant layout
# ---------------------------------------------------------------------------

SLIDE_W, SLIDE_H = 1920, 1080

MARGIN = 20               # outer edge margin
DIVIDER = 2                # divider line thickness between quadrants

# Each quadrant fills roughly half the slide
QUAD_W = (SLIDE_W - MARGIN * 2 - DIVIDER) // 2    # ~949
QUAD_H = (SLIDE_H - MARGIN * 2 - DIVIDER) // 2    # ~529

PHOTO_W, PHOTO_H = 240, 240
PHOTO_GAP = 50             # gap between 2 photos

# BP position order: OG=top-left, OO=top-right, CG=bottom-left, CO=bottom-right
BP_POSITIONS = [
    {"label": "OG", "col": 0, "row": 0},
    {"label": "OO", "col": 1, "row": 0},
    {"label": "CG", "col": 0, "row": 1},
    {"label": "CO", "col": 1, "row": 1},
]

# ---------------------------------------------------------------------------
# Colors — noir palette
# ---------------------------------------------------------------------------

BG_COLOR = (8, 8, 12)
QUAD_BG = (14, 14, 20)
DIVIDER_COLOR = (50, 45, 25)
GOLD = (212, 175, 55)
GOLD_BRIGHT = (240, 210, 80)
GOLD_DIM = (120, 100, 35)
CREAM = (235, 225, 200)
CREAM_DIM = (160, 150, 130)
PHOTO_BORDER = (110, 95, 45)
PHOTO_PLACEHOLDER = (22, 22, 30)
VIGNETTE_STRENGTH = 80
STAR_SEED = 42


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
    for f in photos_path.iterdir():
        if f.stem.lower() == name_lower and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            return f
    return None


def _load_serif(size):
    """Load a serif font, falling back through several options."""
    serif_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/System/Library/Fonts/Times.ttc",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ]
    for path in serif_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
    # Fallback to any available bold font
    sans_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in sans_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


def _draw_starfield(draw, w, h, count=150, seed=STAR_SEED):
    """Subtle starfield dots."""
    rng = _random.Random(seed)
    for _ in range(count):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        b = rng.randint(40, 120)
        draw.point((x, y), fill=(b, b, b + rng.randint(0, 15)))


def _apply_vignette(img):
    """Apply a subtle radial vignette darkening the edges."""
    w, h = img.size
    vignette = Image.new('L', (w, h), 255)
    draw_v = ImageDraw.Draw(vignette)

    cx, cy = w // 2, h // 2
    max_r = (cx ** 2 + cy ** 2) ** 0.5

    steps = 30
    for i in range(steps):
        ratio = i / steps
        r = int(max_r * (1 - ratio * 0.5))
        alpha = int(VIGNETTE_STRENGTH * ratio)
        draw_v.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255 - alpha)

    # Multiply
    from PIL import ImageChops
    black = Image.new('RGB', (w, h), (0, 0, 0))
    img_out = ImageChops.multiply(img, Image.merge('RGB', [vignette, vignette, vignette]))
    return img_out


def _quad_origin(col, row):
    """Top-left corner of a quadrant."""
    x = MARGIN + col * (QUAD_W + DIVIDER)
    y = MARGIN + row * (QUAD_H + DIVIDER)
    return x, y


def _draw_dividers(draw):
    """Draw the thin gold cross-divider lines."""
    # Vertical center line
    vx = MARGIN + QUAD_W
    draw.rectangle([vx, MARGIN, vx + DIVIDER, SLIDE_H - MARGIN], fill=DIVIDER_COLOR)
    # Horizontal center line
    hy = MARGIN + QUAD_H
    draw.rectangle([MARGIN, hy, SLIDE_W - MARGIN, hy + DIVIDER], fill=DIVIDER_COLOR)


def _draw_title_overlay(draw, tournament_name="FIGHT CLUB", round_name=None):
    """Draw tournament name (+ optional round) centered at the cross-divider."""
    font_title = _load_serif(42)
    font_sub = _load_serif(20)

    cx = SLIDE_W // 2
    cy = MARGIN + QUAD_H  # center divider Y

    if round_name:
        # Two lines: tournament name + round
        tw = max(360, len(tournament_name) * 22)
        th = 64
        draw.rectangle([cx - tw // 2, cy - th // 2, cx + tw // 2, cy + th // 2], fill=BG_COLOR)
        draw.text((cx, cy - 14), tournament_name, fill=GOLD, font=font_title, anchor="mm")
        draw.text((cx, cy + 22), round_name, fill=CREAM_DIM, font=font_sub, anchor="mm")
    else:
        # Single line: tournament name only (template)
        tw = max(360, len(tournament_name) * 22)
        th = 44
        draw.rectangle([cx - tw // 2, cy - th // 2, cx + tw // 2, cy + th // 2], fill=BG_COLOR)
        draw.text((cx, cy), tournament_name, fill=GOLD, font=font_title, anchor="mm")


def _draw_speaker_photo(img, draw, speaker_name, photos_dir, cx, y, font):
    """Draw a single speaker photo centered at cx with name below."""
    px = cx - PHOTO_W // 2
    py = y

    # Gold frame
    draw.rounded_rectangle(
        [px - 4, py - 4, px + PHOTO_W + 4, py + PHOTO_H + 4],
        radius=4,
        outline=PHOTO_BORDER,
        width=2,
    )

    photo_path = _find_photo(photos_dir, speaker_name)
    if photo_path:
        try:
            photo = Image.open(photo_path).convert('RGB')
            photo = photo.resize((PHOTO_W, PHOTO_H), Image.LANCZOS)
            img.paste(photo, (px, py))
        except Exception as e:
            logger.warning("Could not load photo for %s: %s", speaker_name, e)
            draw.rectangle([px, py, px + PHOTO_W, py + PHOTO_H], fill=PHOTO_PLACEHOLDER)
    else:
        draw.rectangle([px, py, px + PHOTO_W, py + PHOTO_H], fill=PHOTO_PLACEHOLDER)
        draw.text((cx, py + PHOTO_H // 2), "?", fill=CREAM_DIM, font=font, anchor="mm")

    # Speaker name
    draw.text((cx, py + PHOTO_H + 10), speaker_name, fill=CREAM, font=font, anchor="mt")


def _draw_quadrant(img, draw, pos_info, team_name, speakers, photos_dir):
    """Draw one BP position quadrant spanning its full area."""
    qx, qy = _quad_origin(pos_info["col"], pos_info["row"])

    font_pos = _load_serif(38)
    font_team = _load_serif(20)
    font_speaker = _load_serif(17)

    # Quadrant background
    draw.rectangle([qx, qy, qx + QUAD_W, qy + QUAD_H], fill=QUAD_BG)

    # Layout: position badge + team name centered above photos
    quad_cx = qx + QUAD_W // 2

    # Vertically center the whole block (badge + team name + photos + speaker names)
    badge_h = 40       # position label height
    team_h = 25        # team name height
    gap_label = 8      # gap between team name and photos
    speaker_label_h = 30  # speaker name below photos
    total_block_h = badge_h + team_h + gap_label + PHOTO_H + speaker_label_h
    block_top = qy + (QUAD_H - total_block_h) // 2

    # Position badge — centered
    draw.text((quad_cx, block_top), pos_info["label"], fill=GOLD_BRIGHT, font=font_pos, anchor="mt")

    # Team name — centered below badge
    draw.text((quad_cx, block_top + badge_h), team_name, fill=CREAM, font=font_team, anchor="mt")

    # Photos: centered horizontally
    photo_y = block_top + badge_h + team_h + gap_label
    total_photos_w = PHOTO_W * 2 + PHOTO_GAP
    photos_start_cx = qx + (QUAD_W - total_photos_w) // 2 + PHOTO_W // 2

    for i, speaker in enumerate(speakers[:2]):
        cx = photos_start_cx + i * (PHOTO_W + PHOTO_GAP)
        name = speaker.name if hasattr(speaker, 'name') else speaker
        _draw_speaker_photo(img, draw, name, photos_dir, cx, photo_y, font_speaker)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_background():
    """Generate the background template with 8 placeholder slots."""
    img = Image.new('RGB', (SLIDE_W, SLIDE_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    _draw_starfield(draw, SLIDE_W, SLIDE_H)

    font_pos = _load_serif(38)
    font_team = _load_serif(20)
    font_speaker = _load_serif(17)

    for pos in BP_POSITIONS:
        qx, qy = _quad_origin(pos["col"], pos["row"])
        draw.rectangle([qx, qy, qx + QUAD_W, qy + QUAD_H], fill=QUAD_BG)

        quad_cx = qx + QUAD_W // 2

        # Vertically center the whole block (matching _draw_quadrant layout)
        badge_h = 40
        team_h = 25
        gap_label = 8
        speaker_label_h = 30
        total_block_h = badge_h + team_h + gap_label + PHOTO_H + speaker_label_h
        block_top = qy + (QUAD_H - total_block_h) // 2

        # Position badge — centered
        draw.text((quad_cx, block_top), pos["label"], fill=GOLD_BRIGHT, font=font_pos, anchor="mt")

        # Team name placeholder — centered below badge
        draw.text((quad_cx, block_top + badge_h), "Team Name", fill=CREAM, font=font_team, anchor="mt")

        # Photos: centered horizontally
        photo_y = block_top + badge_h + team_h + gap_label
        total_photos_w = PHOTO_W * 2 + PHOTO_GAP
        photos_start_cx = qx + (QUAD_W - total_photos_w) // 2 + PHOTO_W // 2

        for i in range(2):
            cx = photos_start_cx + i * (PHOTO_W + PHOTO_GAP)
            px = cx - PHOTO_W // 2
            draw.rounded_rectangle(
                [px - 4, photo_y - 4, px + PHOTO_W + 4, photo_y + PHOTO_H + 4],
                radius=4, outline=PHOTO_BORDER, width=2,
            )
            draw.rectangle([px, photo_y, px + PHOTO_W, photo_y + PHOTO_H], fill=PHOTO_PLACEHOLDER)
            draw.text((cx, photo_y + PHOTO_H // 2), f"Speaker {i + 1}",
                       fill=CREAM_DIM, font=font_speaker, anchor="mm")
            draw.text((cx, photo_y + PHOTO_H + 10), "Name",
                       fill=CREAM, font=font_speaker, anchor="mt")

    _draw_dividers(draw)
    img = _apply_vignette(img)
    draw = ImageDraw.Draw(img)
    _draw_title_overlay(draw)

    return img


def generate_round_slide(round_obj, photos_dir, output_dir):
    """Generate a single slide for a round showing all BP positions."""
    from draw.models import Debate, DebateTeam
    from participants.models import Speaker

    debate = Debate.objects.filter(round=round_obj).order_by('pk').first()
    if not debate:
        logger.warning("No debate found for %s", round_obj)
        return None

    img = Image.new('RGB', (SLIDE_W, SLIDE_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    _draw_starfield(draw, SLIDE_W, SLIDE_H)

    debate_teams = list(
        DebateTeam.objects.filter(debate=debate)
        .select_related('team')
        .order_by('side')
    )

    for side_idx, dt in enumerate(debate_teams[:4]):
        if side_idx >= len(BP_POSITIONS):
            break
        pos = BP_POSITIONS[side_idx]
        team = dt.team
        team_name = team.short_name or team.reference
        speakers = list(Speaker.objects.filter(team=team).order_by('pk'))
        _draw_quadrant(img, draw, pos, team_name, speakers, photos_dir)

    _draw_dividers(draw)
    img = _apply_vignette(img)
    draw = ImageDraw.Draw(img)
    tournament_name = round_obj.tournament.short_name or round_obj.tournament.name
    _draw_title_overlay(draw, tournament_name, round_obj.name)

    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"round{round_obj.seq}.png"
    filepath = output_path / filename
    img.save(filepath, "PNG")
    logger.info("Generated slide: %s", filepath)
    return filepath


def generate_round_slide_from_template(round_obj, photos_dir, template_path, output_dir):
    """Generate a slide using a pre-designed template PNG as the background.

    The template provides the full visual design. This function overlays
    photos, speaker names, team names, position labels, and the title.
    """
    from draw.models import Debate, DebateTeam
    from participants.models import Speaker

    debate = Debate.objects.filter(round=round_obj).order_by('pk').first()
    if not debate:
        logger.warning("No debate found for %s", round_obj)
        return None

    img = Image.open(template_path).convert('RGB')
    img = img.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    debate_teams = list(
        DebateTeam.objects.filter(debate=debate)
        .select_related('team')
        .order_by('side')
    )

    font_pos = _load_serif(38)
    font_team = _load_serif(20)
    font_speaker = _load_serif(17)

    for side_idx, dt in enumerate(debate_teams[:4]):
        if side_idx >= len(BP_POSITIONS):
            break
        pos = BP_POSITIONS[side_idx]
        team = dt.team
        team_name = team.short_name or team.reference
        speakers = list(Speaker.objects.filter(team=team).order_by('pk'))

        qx, qy = _quad_origin(pos["col"], pos["row"])
        quad_cx = qx + QUAD_W // 2

        badge_h = 40
        team_h = 25
        gap_label = 8
        speaker_label_h = 30
        total_block_h = badge_h + team_h + gap_label + PHOTO_H + speaker_label_h
        block_top = qy + (QUAD_H - total_block_h) // 2

        # Position label
        draw.text((quad_cx, block_top), pos["label"], fill=GOLD_BRIGHT, font=font_pos, anchor="mt")

        # Team name
        draw.text((quad_cx, block_top + badge_h), team_name, fill=CREAM, font=font_team, anchor="mt")

        # Photos
        photo_y = block_top + badge_h + team_h + gap_label
        total_photos_w = PHOTO_W * 2 + PHOTO_GAP
        photos_start_cx = qx + (QUAD_W - total_photos_w) // 2 + PHOTO_W // 2

        for i, speaker in enumerate(speakers[:2]):
            cx = photos_start_cx + i * (PHOTO_W + PHOTO_GAP)
            name = speaker.name if hasattr(speaker, 'name') else speaker
            _draw_speaker_photo(img, draw, name, photos_dir, cx, photo_y, font_speaker)

    # Title overlay
    tournament_name = round_obj.tournament.short_name or round_obj.tournament.name
    _draw_title_overlay(draw, tournament_name, round_obj.name)

    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"round{round_obj.seq}.png"
    filepath = output_path / filename
    img.save(filepath, "PNG")
    logger.info("Generated slide (template): %s", filepath)
    return filepath


def generate_round_slides(round_obj, photos_dir, output_dir, template_path=None):
    """Generate slides for a round. One slide per round in BP format."""
    if template_path:
        path = generate_round_slide_from_template(round_obj, photos_dir, template_path, output_dir)
    else:
        path = generate_round_slide(round_obj, photos_dir, output_dir)
    return [path] if path else []
