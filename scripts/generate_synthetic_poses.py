"""Generate synthetic hand poses for the ASL alphabet and digits.

Creates approximate 3D joint positions for each letter/number based on
known ASL hand configurations. These serve as fallback poses so --use-3d
works out of the box without external datasets like Kaggle ISLR.

Each pose is saved as a JSON file compatible with HandModel3D.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
POSES_DIR = PROJECT_ROOT / "models" / "hand" / "poses" / "asl"

# Joint names following MediaPipe convention (21 joints)
JOINTS = [
    "wrist",
    "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]

# Base open hand (B-like) positions — all fingers extended
OPEN_HAND = {
    "wrist": (0.50, 0.90, 0.00),
    "thumb_cmc": (0.35, 0.78, 0.03),
    "thumb_mcp": (0.25, 0.65, 0.05),
    "thumb_ip": (0.20, 0.52, 0.06),
    "thumb_tip": (0.17, 0.42, 0.06),
    "index_mcp": (0.32, 0.45, 0.00),
    "index_pip": (0.30, 0.30, 0.00),
    "index_dip": (0.29, 0.20, 0.00),
    "index_tip": (0.29, 0.10, 0.00),
    "middle_mcp": (0.45, 0.42, 0.00),
    "middle_pip": (0.44, 0.26, 0.00),
    "middle_dip": (0.44, 0.16, 0.00),
    "middle_tip": (0.44, 0.06, 0.00),
    "ring_mcp": (0.58, 0.45, 0.00),
    "ring_pip": (0.58, 0.30, 0.00),
    "ring_dip": (0.59, 0.20, 0.00),
    "ring_tip": (0.59, 0.12, 0.00),
    "pinky_mcp": (0.70, 0.50, 0.00),
    "pinky_pip": (0.71, 0.38, 0.00),
    "pinky_dip": (0.72, 0.30, 0.00),
    "pinky_tip": (0.72, 0.22, 0.00),
}


def _curl_finger(base: dict, finger: str, amount: float = 0.8) -> dict:
    """Curl a finger by moving pip/dip/tip toward the palm."""
    result = dict(base)
    prefix = finger
    mcp_key = f"{prefix}_mcp"
    if mcp_key not in result:
        return result

    mx, my, mz = result[mcp_key]
    # pip curls toward palm (increase y, push z forward)
    result[f"{prefix}_pip"] = (mx + 0.01, my + 0.08 * amount, mz + 0.06 * amount)
    result[f"{prefix}_dip"] = (mx + 0.02, my + 0.12 * amount, mz + 0.10 * amount)
    result[f"{prefix}_tip"] = (mx + 0.01, my + 0.10 * amount, mz + 0.12 * amount)
    return result


def _curl_all(base: dict, amount: float = 0.8) -> dict:
    """Curl all four fingers (not thumb)."""
    r = dict(base)
    for f in ["index", "middle", "ring", "pinky"]:
        r = _curl_finger(r, f, amount)
    return r


def _curl_thumb(base: dict, amount: float = 0.8) -> dict:
    """Curl thumb across the palm."""
    r = dict(base)
    cx, cy, cz = r["thumb_cmc"]
    r["thumb_mcp"] = (cx + 0.08 * amount, cy + 0.05 * amount, cz + 0.04 * amount)
    r["thumb_ip"] = (cx + 0.14 * amount, cy + 0.08 * amount, cz + 0.06 * amount)
    r["thumb_tip"] = (cx + 0.18 * amount, cy + 0.06 * amount, cz + 0.07 * amount)
    return r


# ASL letter configurations
def _make_a() -> dict:
    """A: Fist with thumb to the side."""
    r = _curl_all(OPEN_HAND)
    # Thumb extended to the side
    r["thumb_mcp"] = (0.28, 0.65, 0.05)
    r["thumb_ip"] = (0.22, 0.55, 0.04)
    r["thumb_tip"] = (0.20, 0.48, 0.03)
    return r


def _make_b() -> dict:
    """B: Flat hand, fingers together, thumb across palm."""
    r = dict(OPEN_HAND)
    r = _curl_thumb(r, 0.9)
    return r


def _make_c() -> dict:
    """C: Curved hand forming a C shape."""
    r = dict(OPEN_HAND)
    for f in ["index", "middle", "ring", "pinky"]:
        r = _curl_finger(r, f, 0.35)
    r["thumb_mcp"] = (0.30, 0.62, 0.06)
    r["thumb_ip"] = (0.28, 0.52, 0.08)
    r["thumb_tip"] = (0.28, 0.45, 0.08)
    return r


def _make_d() -> dict:
    """D: Index up, other fingers curled to thumb."""
    r = _curl_all(OPEN_HAND)
    # Uncurl index
    r["index_mcp"] = OPEN_HAND["index_mcp"]
    r["index_pip"] = OPEN_HAND["index_pip"]
    r["index_dip"] = OPEN_HAND["index_dip"]
    r["index_tip"] = OPEN_HAND["index_tip"]
    r = _curl_thumb(r, 0.7)
    return r


def _make_e() -> dict:
    """E: All fingers curled, thumb across."""
    r = _curl_all(OPEN_HAND, 0.6)
    r = _curl_thumb(r, 0.5)
    return r


def _make_f() -> dict:
    """F: Thumb and index circle, other fingers up."""
    r = dict(OPEN_HAND)
    # Index and thumb form a circle
    r["index_pip"] = (0.30, 0.38, 0.04)
    r["index_dip"] = (0.28, 0.45, 0.06)
    r["index_tip"] = (0.25, 0.50, 0.06)
    r["thumb_ip"] = (0.23, 0.50, 0.06)
    r["thumb_tip"] = (0.25, 0.52, 0.06)
    return r


def _make_g() -> dict:
    """G: Index pointing sideways, thumb parallel."""
    r = _curl_all(OPEN_HAND)
    r["index_mcp"] = (0.35, 0.50, 0.00)
    r["index_pip"] = (0.25, 0.50, 0.00)
    r["index_dip"] = (0.18, 0.50, 0.00)
    r["index_tip"] = (0.12, 0.50, 0.00)
    r["thumb_mcp"] = (0.35, 0.58, 0.03)
    r["thumb_ip"] = (0.25, 0.58, 0.03)
    r["thumb_tip"] = (0.18, 0.58, 0.03)
    return r


def _make_h() -> dict:
    """H: Index and middle pointing sideways."""
    r = _make_g()
    r["middle_mcp"] = (0.42, 0.48, 0.00)
    r["middle_pip"] = (0.32, 0.46, 0.00)
    r["middle_dip"] = (0.24, 0.45, 0.00)
    r["middle_tip"] = (0.16, 0.45, 0.00)
    return r


def _make_i() -> dict:
    """I: Pinky up, rest curled."""
    r = _curl_all(OPEN_HAND)
    r = _curl_thumb(r, 0.8)
    r["pinky_mcp"] = OPEN_HAND["pinky_mcp"]
    r["pinky_pip"] = OPEN_HAND["pinky_pip"]
    r["pinky_dip"] = OPEN_HAND["pinky_dip"]
    r["pinky_tip"] = OPEN_HAND["pinky_tip"]
    return r


def _make_k() -> dict:
    """K: Index up, middle angled, thumb between."""
    r = _curl_all(OPEN_HAND)
    r["index_mcp"] = OPEN_HAND["index_mcp"]
    r["index_pip"] = OPEN_HAND["index_pip"]
    r["index_dip"] = OPEN_HAND["index_dip"]
    r["index_tip"] = OPEN_HAND["index_tip"]
    r["middle_mcp"] = (0.45, 0.45, 0.00)
    r["middle_pip"] = (0.46, 0.32, 0.03)
    r["middle_dip"] = (0.48, 0.25, 0.05)
    r["middle_tip"] = (0.49, 0.18, 0.06)
    r["thumb_mcp"] = (0.32, 0.55, 0.04)
    r["thumb_ip"] = (0.35, 0.45, 0.05)
    r["thumb_tip"] = (0.38, 0.38, 0.05)
    return r


def _make_l() -> dict:
    """L: L-shape with index and thumb."""
    r = _curl_all(OPEN_HAND)
    r["index_mcp"] = OPEN_HAND["index_mcp"]
    r["index_pip"] = OPEN_HAND["index_pip"]
    r["index_dip"] = OPEN_HAND["index_dip"]
    r["index_tip"] = OPEN_HAND["index_tip"]
    r["thumb_mcp"] = (0.28, 0.70, 0.03)
    r["thumb_ip"] = (0.18, 0.68, 0.03)
    r["thumb_tip"] = (0.12, 0.68, 0.03)
    return r


def _make_o() -> dict:
    """O: All fingertips touching thumb tip, forming O."""
    r = dict(OPEN_HAND)
    center = (0.40, 0.45, 0.06)
    for f in ["index", "middle", "ring", "pinky"]:
        r = _curl_finger(r, f, 0.45)
        r[f"{f}_tip"] = (center[0] + 0.02, center[1], center[2])
    r["thumb_tip"] = (center[0] - 0.02, center[1], center[2])
    r["thumb_ip"] = (0.32, 0.50, 0.05)
    return r


def _make_r() -> dict:
    """R: Index and middle crossed."""
    r = _curl_all(OPEN_HAND)
    r = _curl_thumb(r, 0.8)
    r["index_mcp"] = OPEN_HAND["index_mcp"]
    r["index_pip"] = (0.32, 0.30, 0.00)
    r["index_dip"] = (0.35, 0.20, 0.00)
    r["index_tip"] = (0.37, 0.12, 0.00)
    r["middle_mcp"] = OPEN_HAND["middle_mcp"]
    r["middle_pip"] = (0.40, 0.28, 0.02)
    r["middle_dip"] = (0.37, 0.18, 0.03)
    r["middle_tip"] = (0.34, 0.10, 0.03)
    return r


def _make_s() -> dict:
    """S: Fist with thumb over fingers."""
    r = _curl_all(OPEN_HAND, 0.9)
    r = _curl_thumb(r, 0.6)
    r["thumb_tip"] = (0.40, 0.55, 0.08)
    return r


def _make_u() -> dict:
    """U: Index and middle up together."""
    r = _curl_all(OPEN_HAND)
    r = _curl_thumb(r, 0.8)
    r["index_mcp"] = OPEN_HAND["index_mcp"]
    r["index_pip"] = OPEN_HAND["index_pip"]
    r["index_dip"] = OPEN_HAND["index_dip"]
    r["index_tip"] = OPEN_HAND["index_tip"]
    r["middle_mcp"] = OPEN_HAND["middle_mcp"]
    r["middle_pip"] = OPEN_HAND["middle_pip"]
    r["middle_dip"] = OPEN_HAND["middle_dip"]
    r["middle_tip"] = OPEN_HAND["middle_tip"]
    return r


def _make_v() -> dict:
    """V: Index and middle spread (peace sign)."""
    r = _make_u()
    # Spread fingers apart
    r["index_pip"] = (0.24, 0.28, 0.00)
    r["index_dip"] = (0.20, 0.18, 0.00)
    r["index_tip"] = (0.18, 0.08, 0.00)
    r["middle_pip"] = (0.50, 0.26, 0.00)
    r["middle_dip"] = (0.52, 0.16, 0.00)
    r["middle_tip"] = (0.54, 0.06, 0.00)
    return r


def _make_w() -> dict:
    """W: Index, middle, ring spread."""
    r = _make_v()
    r["ring_mcp"] = OPEN_HAND["ring_mcp"]
    r["ring_pip"] = (0.64, 0.30, 0.00)
    r["ring_dip"] = (0.67, 0.20, 0.00)
    r["ring_tip"] = (0.69, 0.12, 0.00)
    return r


def _make_y() -> dict:
    """Y: Thumb and pinky out (shaka)."""
    r = _curl_all(OPEN_HAND, 0.85)
    r["pinky_mcp"] = OPEN_HAND["pinky_mcp"]
    r["pinky_pip"] = OPEN_HAND["pinky_pip"]
    r["pinky_dip"] = OPEN_HAND["pinky_dip"]
    r["pinky_tip"] = OPEN_HAND["pinky_tip"]
    r["thumb_mcp"] = (0.22, 0.68, 0.04)
    r["thumb_ip"] = (0.14, 0.62, 0.04)
    r["thumb_tip"] = (0.08, 0.58, 0.04)
    return r


# Map letters to pose generators
LETTER_POSES = {
    "a": _make_a,
    "b": _make_b,
    "c": _make_c,
    "d": _make_d,
    "e": _make_e,
    "f": _make_f,
    "g": _make_g,
    "h": _make_h,
    "i": _make_i,
    # J is J motion (same start as I) — use I pose
    "j": _make_i,
    "k": _make_k,
    "l": _make_l,
    # M, N, T are fist variants
    "m": _make_s,
    "n": _make_s,
    "o": _make_o,
    # P is similar to K but pointing down
    "p": _make_k,
    # Q is similar to G but pointing down
    "q": _make_g,
    "r": _make_r,
    "s": _make_s,
    # T is fist with thumb between index/middle
    "t": _make_a,
    "u": _make_u,
    "v": _make_v,
    "w": _make_w,
    # X is index hooked
    "x": _make_d,
    "y": _make_y,
    # Z is index tracing Z shape (use D as base)
    "z": _make_d,
}


def _make_number(n: int) -> dict:
    """Generate a pose for a digit (0-9)."""
    if n == 0:
        return _make_o()
    if n == 1:
        return _make_d()  # Index up
    if n == 2:
        return _make_v()  # Peace/2
    if n == 3:
        return _make_w()  # 3 fingers + thumb
    if n == 4:
        # 4 fingers up, thumb curled
        r = dict(OPEN_HAND)
        r = _curl_thumb(r, 0.9)
        return r
    if n == 5:
        return dict(OPEN_HAND)  # Open hand
    if n == 6:
        # Pinky down touching thumb
        r = dict(OPEN_HAND)
        r["pinky_pip"] = (0.65, 0.50, 0.04)
        r["pinky_dip"] = (0.58, 0.55, 0.06)
        r["pinky_tip"] = (0.50, 0.55, 0.07)
        r["thumb_tip"] = (0.48, 0.55, 0.07)
        return r
    if n == 7:
        # Ring down touching thumb
        r = dict(OPEN_HAND)
        r["ring_pip"] = (0.55, 0.48, 0.04)
        r["ring_dip"] = (0.50, 0.52, 0.06)
        r["ring_tip"] = (0.45, 0.53, 0.07)
        r["thumb_tip"] = (0.43, 0.53, 0.07)
        return r
    if n == 8:
        # Middle down touching thumb
        r = dict(OPEN_HAND)
        r["middle_pip"] = (0.44, 0.38, 0.04)
        r["middle_dip"] = (0.42, 0.44, 0.06)
        r["middle_tip"] = (0.38, 0.48, 0.07)
        r["thumb_tip"] = (0.36, 0.48, 0.07)
        return r
    # n == 9: Index down touching thumb
    r = dict(OPEN_HAND)
    r["index_pip"] = (0.30, 0.40, 0.04)
    r["index_dip"] = (0.30, 0.48, 0.06)
    r["index_tip"] = (0.32, 0.52, 0.07)
    r["thumb_tip"] = (0.34, 0.52, 0.07)
    return r


def save_pose(sign_id: str, name: str, joints: dict, output_dir: Path) -> None:
    """Save a pose as a JSON file."""
    # Convert tuples to lists for JSON serialization
    joints_json = {k: list(v) for k, v in joints.items()}
    pose_data = {
        "name": name,
        "sign_id": sign_id,
        "joints": joints_json,
        "source": "synthetic",
        "image_file": None,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / f"{sign_id}.json", "w") as f:
        json.dump(pose_data, f, indent=2)


def main() -> None:
    print("Generating synthetic ASL hand poses...")

    # Letters
    for letter, make_fn in LETTER_POSES.items():
        joints = make_fn()
        save_pose(letter, f"Letter {letter.upper()}", joints, POSES_DIR)
    print(f"  Generated {len(LETTER_POSES)} letter poses")

    # Numbers
    for digit in range(10):
        joints = _make_number(digit)
        save_pose(str(digit), f"Number {digit}", joints, POSES_DIR)
    print("  Generated 10 number poses")

    print(f"  Saved to: {POSES_DIR}")
    print("  Use with: python main.py -s subtitles.srt --use-3d")


if __name__ == "__main__":
    main()
