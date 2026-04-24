WEAPON_SCALING = {
    "wand": [
        dict(damage=15,  range=6,  cooldown=4, projectiles=1, shot_delay=2),  # 1
        dict(damage=20,  range=6,  cooldown=4, projectiles=1, shot_delay=2),  # 2
        dict(damage=25,  range=7,  cooldown=4, projectiles=2, shot_delay=2),  # 3
        dict(damage=30,  range=7,  cooldown=3, projectiles=2, shot_delay=2),  # 4
        dict(damage=38,  range=7,  cooldown=3, projectiles=3, shot_delay=2),  # 5
        dict(damage=46,  range=7,  cooldown=3, projectiles=3, shot_delay=1),  # 6
        dict(damage=55,  range=8,  cooldown=2, projectiles=4, shot_delay=1),  # 7
        dict(damage=65,  range=8,  cooldown=2, projectiles=4, shot_delay=1),  # 8
        dict(damage=78,  range=9,  cooldown=2, projectiles=5, shot_delay=1),  # 9
        dict(damage=95,  range=10, cooldown=1, projectiles=5, shot_delay=1),  # 10
    ],
    "axe": [
        dict(damage=25,  cooldown=5, projectiles=1),
        dict(damage=33,  cooldown=5, projectiles=1),
        dict(damage=42,  cooldown=4, projectiles=2),
        dict(damage=52,  cooldown=4, projectiles=2),
        dict(damage=64,  cooldown=4, projectiles=3),
        dict(damage=78,  cooldown=3, projectiles=3),
        dict(damage=94,  cooldown=3, projectiles=4),
        dict(damage=112, cooldown=3, projectiles=4),
        dict(damage=133, cooldown=2, projectiles=5),
        dict(damage=160, cooldown=2, projectiles=5),
    ],
    "whip": [
        dict(damage=12,  range=2, cooldown=8,  burst=1),
        dict(damage=16,  range=2, cooldown=8,  burst=1),
        dict(damage=20,  range=3, cooldown=8,  burst=2),
        dict(damage=25,  range=3, cooldown=8,  burst=2),
        dict(damage=31,  range=3, cooldown=7,  burst=3),
        dict(damage=38,  range=4, cooldown=7,  burst=3),
        dict(damage=46,  range=4, cooldown=7,  burst=4),
        dict(damage=55,  range=4, cooldown=6,  burst=4),
        dict(damage=65,  range=5, cooldown=6,  burst=5),
        dict(damage=78,  range=5, cooldown=6,  burst=5),
    ],
    "books": [
        dict(damage=8,   range=2, cooldown=1, orbs=3),
        dict(damage=11,  range=2, cooldown=1, orbs=3),
        dict(damage=14,  range=3, cooldown=1, orbs=3),
        dict(damage=18,  range=3, cooldown=1, orbs=4),
        dict(damage=22,  range=3, cooldown=1, orbs=4),
        dict(damage=27,  range=4, cooldown=1, orbs=4),
        dict(damage=33,  range=4, cooldown=1, orbs=4),
        dict(damage=40,  range=4, cooldown=1, orbs=5),
        dict(damage=48,  range=5, cooldown=1, orbs=5),
        dict(damage=58,  range=5, cooldown=1, orbs=6),
    ],
    # Shield scaling kept for future work not in active weapon pool
    "shield": [
        dict(block_chance=0.50),
        dict(block_chance=0.55),
        dict(block_chance=0.60),
        dict(block_chance=0.65),
        dict(block_chance=0.70),
        dict(block_chance=0.74),
        dict(block_chance=0.78),
        dict(block_chance=0.82),
        dict(block_chance=0.86),
        dict(block_chance=0.90),
    ],
}

# ── Base weapon definitions ────────────────────────────────────
# Shield excluded: 0 DPS, block never triggers, wastes a weapon slot as weapon is underpowered and doesn't fit current agent strategy. Can be re added once the environment and agent are expanded to support more defensive playstyles.
WEAPON_POOL = {
    "wand": {
        "name":       "Magic Wand",
        "type":       "target",
        "timer":      0,
        "angle":      0.0,
        "level":      1,
        "shot_queue": [],
        **WEAPON_SCALING["wand"][0],
    },
    "axe": {
        "name":       "Axe",
        "type":       "arc",
        "timer":      0,
        "angle":      0.0,
        "level":      1,
        **WEAPON_SCALING["axe"][0],
    },
    "whip": {
        "name":            "Whip",
        "type":            "directional",
        "timer":           0,
        "angle":           0.0,
        "level":           1,
        "burst_remaining": 0,
        "burst_timer":     0,
        **WEAPON_SCALING["whip"][0],
    },
    "books": {
        "name":    "Spell Books",
        "type":    "orbit",
        "timer":   0,
        "angle":   0.0,
        "level":   1,
        **WEAPON_SCALING["books"][0],
    },
}


def get_random_starting_weapon():
    import random
    key  = random.choice(list(WEAPON_POOL.keys()))
    data = {k: (list(v) if isinstance(v, list) else v)
            for k, v in WEAPON_POOL[key].items()}
    return key, data


def apply_level_up(weapon_key, weapon_data):
    """Apply next level stats from scaling table. Caps at 10."""
    current = weapon_data["level"]
    if current >= 10:
        return False
    new_level = current + 1
    scale     = WEAPON_SCALING[weapon_key][new_level - 1]
    weapon_data["level"] = new_level
    for stat, val in scale.items():
        weapon_data[stat] = val
    if weapon_key == "wand" and "shot_queue" not in weapon_data:
        weapon_data["shot_queue"] = []
    if weapon_key == "whip":
        if "burst_remaining" not in weapon_data:
            weapon_data["burst_remaining"] = 0
            weapon_data["burst_timer"]     = 0
    return True


def weapon_stats_summary(key, weapon_data):
    lvl = weapon_data["level"]
    if key == "shield":
        return f"Block: {int(weapon_data['block_chance']*100)}%"
    parts = [f"Dmg:{weapon_data['damage']}"]
    if "range"       in weapon_data: parts.append(f"Rng:{weapon_data['range']}")
    if "cooldown"    in weapon_data: parts.append(f"CD:{weapon_data['cooldown']}")
    if "projectiles" in weapon_data: parts.append(f"x{weapon_data['projectiles']}")
    if "burst"       in weapon_data: parts.append(f"Burst:{weapon_data['burst']}")
    if "orbs"        in weapon_data: parts.append(f"Orbs:{weapon_data['orbs']}")
    return "  ".join(parts)