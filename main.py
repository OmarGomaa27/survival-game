import pygame
import sys
import random
import math
import json
import os

try:
    from enemy import spawn_enemies, Enemy
except ImportError:
    from game.enemy import spawn_enemies, Enemy

try:
    from rl.q_tabular import QLearningAgent, WeaponChoiceAgent
    from game.weapons import (WEAPON_POOL, WEAPON_SCALING,
                               get_random_starting_weapon,
                               apply_level_up, weapon_stats_summary)
    from game.stats import RunTracker
except ImportError:
    from q_tabular import QLearningAgent, WeaponChoiceAgent
    from weapons import (WEAPON_POOL, WEAPON_SCALING,
                         get_random_starting_weapon,
                         apply_level_up, weapon_stats_summary)
    from stats import RunTracker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE              = 24
FPS               = 8
FOG_RADIUS        = 3
MAX_EPISODES      = 20000
MAX_TICKS         = 1000
AGENT_MOVE_EVERY  = 3
BOSS_WAVES        = {3, 6, 9, 12, 15}
MAX_WEAPON_SLOTS  = 3
BURST_INTER_DELAY = 2

TRAINING  = True
FAST_MODE = False

# Colors
BLACK     = (0,   0,   0)
DARK_GREY = (30,  30,  30)
GREY      = (60,  60,  60)
WHITE     = (255, 255, 255)
GREEN     = (50,  200, 50)
YELLOW    = (255, 220, 0)
BLUE      = (100, 180, 255)
CYAN      = (80,  220, 220)
RED       = (200, 50,  50)
ORANGE    = (255, 140, 0)
PURPLE    = (180, 0,   220)
GOLD      = (255, 200, 50)
DIM_GREEN = (30,  120, 30)

# ---------------------------------------------------------------------------
# Map layout (1 = wall, 0 = walkable)
# ---------------------------------------------------------------------------
MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
ROWS = len(MAP)
COLS = len(MAP[0])
W    = COLS * TILE
H    = ROWS * TILE

# Precompute total walkable tiles for exploration percentage
TOTAL_WALKABLE = sum(1 for r in range(ROWS) for c in range(COLS)
                     if MAP[r][c] == 0)

# ---------------------------------------------------------------------------
# Screen (larger than the game map, resizable)
# ---------------------------------------------------------------------------
SCREEN_W = 800
SCREEN_H = 680

# ---------------------------------------------------------------------------
# Sprite loading helper
# ---------------------------------------------------------------------------
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

def load_sprite(filename):
    """Load and scale a sprite from the assets directory.
    Returns None if the file is missing so the game can fall back
    to primitive shape rendering."""
    path = os.path.join(ASSET_DIR, filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, (TILE, TILE))
    except Exception as e:
        print(f"Warning: could not load {filename}: {e}")
        return None

# ---------------------------------------------------------------------------
# Fog of war / exploration
# ---------------------------------------------------------------------------
def update_seen_tiles(agent, seen_tiles):
    """Mark tiles within FOG_RADIUS as seen.  Only checks the small
    bounding box around the agent to keep fast-mode training performant."""
    new_count = 0
    r = FOG_RADIUS
    min_row = max(0, agent.y - r)
    max_row = min(ROWS - 1, agent.y + r)
    min_col = max(0, agent.x - r)
    max_col = min(COLS - 1, agent.x + r)
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            if (col, row) not in seen_tiles:
                dist_sq = (col - agent.x)**2 + (row - agent.y)**2
                if dist_sq <= r * r:
                    seen_tiles.add((col, row))
                    new_count += 1
    return new_count

# ---------------------------------------------------------------------------
# Gem helpers
# ---------------------------------------------------------------------------
def spawn_gems(n, cols, rows, game_map, exclude_positions=None):
    if exclude_positions is None:
        exclude_positions = []
    gems, excluded = [], set(exclude_positions)
    attempts = 0
    while len(gems) < n and attempts < 1000:
        x = random.randint(1, cols - 2)
        y = random.randint(1, rows - 2)
        if game_map[y][x] == 0 and (x, y) not in excluded and (x, y) not in gems:
            gems.append((x, y))
        attempts += 1
    return gems

def drop_gem(enemy, gems):
    pos = (enemy.x, enemy.y)
    if pos not in gems:
        gems.append(pos)

def drop_boss_gems(enemy, gems, game_map):
    """Drop a cluster of gems around a defeated boss."""
    offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),
               (1,1),(-1,1),(1,-1),(-1,-1),(2,0)]
    for dx, dy in offsets:
        nx, ny = enemy.x + dx, enemy.y + dy
        if (0 <= nx < COLS and 0 <= ny < ROWS
                and game_map[ny][nx] == 0
                and (nx, ny) not in gems):
            gems.append((nx, ny))

def spawn_boss(agent, game_map, cols, rows):
    """Place a boss as far from the agent as possible."""
    attempts, best_pos, best_dist = 0, None, 0
    while attempts < 500:
        x = random.randint(1, cols - 2)
        y = random.randint(1, rows - 2)
        if game_map[y][x] == 0:
            dist = abs(x - agent.x) + abs(y - agent.y)
            if dist >= 8 and dist > best_dist:
                best_dist, best_pos = dist, (x, y)
        attempts += 1
    if best_pos:
        return Enemy(best_pos[0], best_pos[1],
                     hp=300, damage=25, speed=3,
                     color=PURPLE, symbol="B")
    return None

# ---------------------------------------------------------------------------
# Weapon handlers
# ---------------------------------------------------------------------------
def handle_wand(agent, weapon, enemies, gems, tick_count,
                ep_stats=None, weapon_key="wand"):
    """Auto-targeting projectile weapon. Fires at the nearest enemy
    within range on cooldown."""
    nk = bk = 0
    if "shot_queue" not in weapon:
        weapon["shot_queue"] = []
    weapon["timer"] += 1
    if weapon["timer"] >= weapon["cooldown"]:
        weapon["timer"] = 0
        n     = weapon.get("projectiles", 1)
        delay = weapon.get("shot_delay", 2)
        for i in range(n):
            weapon["shot_queue"].append(tick_count + i * delay)
    fired = []
    for fire_tick in weapon["shot_queue"]:
        if tick_count >= fire_tick:
            fired.append(fire_tick)
            nearest, best = None, float("inf")
            for e in enemies:
                d = ((e.x - agent.x)**2 + (e.y - agent.y)**2) ** 0.5
                if d <= weapon["range"] and d < best:
                    best, nearest = d, e
            if nearest:
                is_boss = nearest.symbol == "B"
                dmg     = weapon["damage"]
                nearest.take_damage(dmg)
                if ep_stats:
                    ep_stats.record_damage(weapon_key, dmg)
                if not nearest.alive:
                    enemies.remove(nearest)
                    if is_boss:
                        drop_boss_gems(nearest, gems, MAP)
                        bk += 1
                    else:
                        drop_gem(nearest, gems)
                        nk += 1
    for ft in fired:
        weapon["shot_queue"].remove(ft)
    return nk, bk

def spawn_axe_volley(agent, weapon):
    """Create arc projectiles that travel upward then fall with gravity."""
    n   = weapon.get("projectiles", 1)
    dmg = weapon["damage"]
    if n == 1:
        vx_vals = [0.0]
    else:
        spread  = 0.5 * (n - 1)
        vx_vals = [-spread / 2 + spread / (n - 1) * i for i in range(n)]
    projs = []
    for vx in vx_vals:
        projs.append({
            "type": "axe", "x": float(agent.x), "y": float(agent.y),
            "vx": vx, "vy": -1.8, "gravity": 0.18, "damage": dmg,
            "start_y": agent.y, "hit_ids": set(), "alive": True,
        })
    return projs

def handle_axe(agent, weapon, active_projectiles):
    weapon["timer"] += 1
    if weapon["timer"] >= weapon["cooldown"]:
        weapon["timer"] = 0
        active_projectiles.extend(spawn_axe_volley(agent, weapon))

def update_projectiles(active_projectiles, enemies, gems, ep_stats=None):
    """Advance all active projectiles, check collisions, remove dead ones."""
    nk = bk = 0
    for proj in active_projectiles:
        if not proj["alive"]:
            continue
        proj["x"]  += proj["vx"]
        proj["y"]  += proj["vy"]
        proj["vy"] += proj["gravity"]
        gx = int(round(proj["x"]))
        gy = int(round(proj["y"]))
        if not (0 <= gx < COLS and 0 <= gy < ROWS):
            proj["alive"] = False
            continue
        if MAP[gy][gx] == 1:
            proj["alive"] = False
            continue
        if proj["vy"] > 0 and proj["y"] >= proj["start_y"] + 0.5:
            proj["alive"] = False
            continue
        for e in list(enemies):
            if id(e) in proj["hit_ids"]:
                continue
            if e.x == gx and e.y == gy:
                proj["hit_ids"].add(id(e))
                is_boss = e.symbol == "B"
                dmg     = proj["damage"]
                e.take_damage(dmg)
                if ep_stats:
                    ep_stats.record_damage("axe", dmg)
                if not e.alive:
                    enemies.remove(e)
                    if is_boss:
                        drop_boss_gems(e, gems, MAP)
                        bk += 1
                    else:
                        drop_gem(e, gems)
                        nk += 1
    active_projectiles[:] = [p for p in active_projectiles if p["alive"]]
    return nk, bk

def handle_whip(agent, weapon, enemies, gems,
                ep_stats=None, weapon_key="whip"):
    """Directional melee weapon that strikes enemies in front of the agent."""
    nk = bk = 0
    if "burst_remaining" not in weapon:
        weapon["burst_remaining"] = 0
        weapon["burst_timer"]     = 0
    weapon["timer"] += 1
    if weapon["timer"] >= weapon["cooldown"] and weapon["burst_remaining"] == 0:
        weapon["timer"]           = 0
        weapon["burst_remaining"] = weapon.get("burst", 1)
        weapon["burst_timer"]     = BURST_INTER_DELAY
    if weapon["burst_remaining"] > 0:
        weapon["burst_timer"] += 1
        if weapon["burst_timer"] >= BURST_INTER_DELAY:
            weapon["burst_timer"]     = 0
            weapon["burst_remaining"] -= 1
            dx, dy = agent.facing
            for e in list(enemies):
                rx, ry   = e.x - agent.x, e.y - agent.y
                in_front = (
                    (dx != 0 and rx * dx > 0 and abs(ry) <= 1) or
                    (dy != 0 and ry * dy > 0 and abs(rx) <= 1)
                )
                if in_front and abs(rx) + abs(ry) <= weapon["range"]:
                    is_boss = e.symbol == "B"
                    dmg     = weapon["damage"]
                    e.take_damage(dmg)
                    if ep_stats:
                        ep_stats.record_damage(weapon_key, dmg)
                    if not e.alive:
                        enemies.remove(e)
                        if is_boss:
                            drop_boss_gems(e, gems, MAP)
                            bk += 1
                        else:
                            drop_gem(e, gems)
                            nk += 1
    return nk, bk

def handle_books(agent, weapon, enemies, gems,
                 ep_stats=None, weapon_key="books"):
    """Orbiting projectiles that rotate around the agent and damage
    enemies on contact."""
    weapon["angle"] += 0.18
    nk = bk = 0
    positions = []
    n_orbs = weapon.get("orbs", 3)
    for i in range(n_orbs):
        angle = weapon["angle"] + (i * 2 * math.pi / n_orbs)
        bx = agent.x + int(round(math.cos(angle) * weapon["range"]))
        by = agent.y + int(round(math.sin(angle) * weapon["range"]))
        positions.append((bx, by))
        for e in list(enemies):
            if e.x == bx and e.y == by:
                is_boss = e.symbol == "B"
                dmg     = weapon["damage"]
                e.take_damage(dmg)
                if ep_stats:
                    ep_stats.record_damage(weapon_key, dmg)
                if not e.alive:
                    enemies.remove(e)
                    if is_boss:
                        drop_boss_gems(e, gems, MAP)
                        bk += 1
                    else:
                        drop_gem(e, gems)
                        nk += 1
    return nk, bk, positions

def try_block_with_shield(agent, weapons, enemy, ep_stats=None):
    """Attempt to block an incoming attack if the agent has a shield
    and is facing the attacker."""
    for weapon in weapons.values():
        if weapon["type"] != "defense":
            continue
        dx, dy   = agent.facing
        ix, iy   = enemy.x - agent.x, enemy.y - agent.y
        in_front = (dx != 0 and ix * dx > 0) or (dy != 0 and iy * dy > 0)
        if in_front and random.random() < weapon["block_chance"]:
            if ep_stats:
                ep_stats.record_block("shield", enemy.damage)
            return True
    return False

# ---------------------------------------------------------------------------
# Weapon selection (heuristic -- to be replaced by WeaponChoiceAgent)
# ---------------------------------------------------------------------------
def weighted_weapon_choice(choices, weapons, tracker):
    """Pick a level-up option weighted by historical win rate and DPS.
    Falls back to uniform weight (0.15) until a weapon has 3000+
    appearances in the tracker."""
    weights = []
    for kind, key in choices:
        apps = tracker.weapon_appearances(key)
        has_data = apps > 3000
        if key == "shield":
            avg_saved = tracker.weapon_avg_hp_saved(key)
            w = min(avg_saved / 50.0, 1.0) if has_data else 0.15
        elif kind == "new":
            wr = tracker.weapon_win_rate(key)
            w  = wr if has_data else 0.15
        else:
            wr       = tracker.weapon_win_rate(key)
            adps     = tracker.weapon_avg_dps(key)
            dps_norm = min(adps / 5.0, 1.0)
            w = (wr * 0.7) + (dps_norm * 0.3) if has_data else 0.15
        weights.append(max(w, 0.01))
    total = sum(weights)
    r     = random.random() * total
    cumul = 0.0
    picked = len(choices) - 1
    for i, w in enumerate(weights):
        cumul += w
        if r <= cumul:
            picked = i
            break
    return picked, weights

# ---------------------------------------------------------------------------
# Level-up system
# ---------------------------------------------------------------------------
def generate_level_up_choices(weapons):
    """Build up to 3 level-up options: new weapons and/or upgrades."""
    owned_keys   = list(weapons.keys())
    unowned_keys = [k for k in WEAPON_POOL if k not in weapons]
    empty_slots  = MAX_WEAPON_SLOTS - len(weapons)
    pool = []
    if empty_slots > 0 and unowned_keys:
        new_picks = random.sample(unowned_keys, min(len(unowned_keys), 2))
        pool += [("new", k) for k in new_picks]
    upgradeable = [k for k in owned_keys if weapons[k]["level"] < 10]
    if upgradeable:
        pool += [("upgrade", k)
                 for k in random.sample(upgradeable, min(len(upgradeable), 3))]
    random.shuffle(pool)
    seen, choices = set(), []
    for item in pool:
        if item not in seen and len(choices) < 3:
            seen.add(item)
            choices.append(item)
    while len(choices) < 3 and upgradeable:
        fallback = [("upgrade", k) for k in upgradeable
                    if ("upgrade", k) not in choices]
        if not fallback:
            break
        choices.append(random.choice(fallback))
    return choices

def apply_choice(choice, weapons):
    kind, key = choice
    if kind == "new":
        weapons[key] = {k: (list(v) if isinstance(v, list) else v)
                        for k, v in WEAPON_POOL[key].items()}
    elif kind == "upgrade" and key in weapons:
        apply_level_up(key, weapons[key])

# ---------------------------------------------------------------------------
# Level-up UI (manual / play mode)
# ---------------------------------------------------------------------------
def draw_level_up_screen(surface, choices, weapons):
    sw, sh = surface.get_size()
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surface.blit(overlay, (0, 0))
    ft = pygame.font.SysFont(None, 40)
    fc = pygame.font.SysFont(None, 26)
    fh = pygame.font.SysFont(None, 20)
    title = ft.render("LEVEL UP -- Choose Weapon", True, GOLD)
    surface.blit(title, (sw // 2 - title.get_width() // 2, 35))
    card_w, card_h = 160, 160
    gap    = 20
    start_x = sw // 2 - (3 * card_w + 2 * gap) // 2
    card_y  = sh // 2 - card_h // 2
    rects = []
    for i, (kind, key) in enumerate(choices):
        cx   = start_x + i * (card_w + gap)
        rect = pygame.Rect(cx, card_y, card_w, card_h)
        rects.append(rect)
        bg   = (15, 55, 15) if kind == "new" else (40, 15, 60)
        pygame.draw.rect(surface, bg,   rect, border_radius=8)
        pygame.draw.rect(surface, GOLD, rect, 2, border_radius=8)
        w_data    = weapons[key] if key in weapons else WEAPON_POOL[key]
        cur_level = w_data["level"]
        new_level = cur_level + 1 if kind == "upgrade" else 1
        num = fc.render(f"[{i+1}]", True, GOLD)
        surface.blit(num, (cx + card_w // 2 - num.get_width() // 2, card_y + 8))
        name_surf = fc.render(WEAPON_POOL[key]["name"], True, WHITE)
        if name_surf.get_width() > card_w - 8:
            name_surf = fh.render(WEAPON_POOL[key]["name"], True, WHITE)
        surface.blit(name_surf,
                     (cx + card_w // 2 - name_surf.get_width() // 2, card_y + 32))
        badge = (fh.render("NEW WEAPON", True, GREEN) if kind == "new"
                 else fh.render(f"Lv {cur_level} -> {new_level}", True, CYAN))
        surface.blit(badge,
                     (cx + card_w // 2 - badge.get_width() // 2, card_y + 54))
        scale = WEAPON_SCALING[key][new_level - 1]
        if key == "shield":
            s1 = fh.render(f"Block: {int(scale['block_chance']*100)}%",
                           True, YELLOW)
            surface.blit(s1, (cx + card_w // 2 - s1.get_width() // 2, card_y + 76))
        else:
            lines = [f"DMG: {scale['damage']}"]
            if "range"       in scale: lines.append(f"RNG:{scale['range']}")
            if "cooldown"    in scale: lines.append(f"CD:{scale['cooldown']}")
            if "projectiles" in scale: lines.append(f"x{scale['projectiles']} shots")
            if "burst"       in scale: lines.append(f"Burst:{scale['burst']}")
            if "orbs"        in scale: lines.append(f"Orbs:{scale['orbs']}")
            for j, ln in enumerate(lines[:3]):
                s = fh.render(ln, True, YELLOW if j == 0 else GREY)
                surface.blit(s, (cx + card_w // 2 - s.get_width() // 2,
                                  card_y + 76 + j * 18))
        if kind == "upgrade" and cur_level >= 9:
            mx = fh.render("MAX NEXT", True, ORANGE)
            surface.blit(mx, (cx + card_w // 2 - mx.get_width() // 2,
                               card_y + card_h - 18))
    hint = fh.render("Press 1 / 2 / 3  or  click a card", True, GREY)
    surface.blit(hint, (sw // 2 - hint.get_width() // 2, card_y + card_h + 14))
    pygame.display.flip()
    return rects

def run_level_up_ui(surface, choices, weapons):
    while True:
        rects = draw_level_up_screen(surface, choices, weapons)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: return 0
                if event.key == pygame.K_2: return 1
                if event.key == pygame.K_3: return 2
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos): return i

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp        = 100
        self.facing    = (0, -1)

    def move(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and MAP[ny][nx] == 0:
            self.x, self.y = nx, ny
            if (dx, dy) != (0, 0):
                self.facing = (dx, dy)

    def draw(self, surface, font):
        rect  = pygame.Rect(self.x * TILE, self.y * TILE, TILE, TILE)
        pygame.draw.rect(surface, GREEN, rect)
        label = font.render("@", True, WHITE)
        surface.blit(label, (self.x * TILE + 8, self.y * TILE + 6))

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def draw_map(surface):
    for row in range(ROWS):
        for col in range(COLS):
            color = GREY if MAP[row][col] == 1 else DARK_GREY
            rect  = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, BLACK, rect, 1)

def draw_fog(surface, agent):
    fog = pygame.Surface((W, H), pygame.SRCALPHA)
    fog.fill((0, 0, 0, 240))
    for row in range(ROWS):
        for col in range(COLS):
            dist = ((col - agent.x)**2 + (row - agent.y)**2) ** 0.5
            if dist <= FOG_RADIUS:
                pygame.draw.rect(fog, (0, 0, 0, 0),
                                 (col * TILE, row * TILE, TILE, TILE))
    surface.blit(fog, (0, 0))

def draw_projectiles(surface, active_projectiles):
    for proj in active_projectiles:
        if not proj["alive"]:
            continue
        gx = int(round(proj["x"]))
        gy = int(round(proj["y"]))
        if 0 <= gx < COLS and 0 <= gy < ROWS:
            rect = pygame.Rect(gx * TILE + 4, gy * TILE + 4, TILE - 8, TILE - 8)
            pygame.draw.rect(surface, ORANGE, rect, border_radius=3)
            pygame.draw.rect(surface, GOLD,   rect, 1, border_radius=3)

def draw_hud(surface, agent, wave, kills, xp, xp_level,
             weapons, episode, episode_reward, epsilon,
             fast_mode, boss_alive):
    sw = surface.get_width()
    font        = pygame.font.SysFont(None, 26)
    weapon_text = "  ".join(
        f"{w['name']} Lv{w['level']}" for w in weapons.values())
    mode_label  = "FAST" if fast_mode else ("TRAIN" if TRAINING else "MANUAL")
    mode_color  = ORANGE if fast_mode else \
                  ((255, 180, 0) if TRAINING else (100, 255, 100))
    left_lines = [
        (f"HP: {agent.hp}",             WHITE),
        (f"Wave: {wave}",               WHITE),
        (f"Kills: {kills}",             WHITE),
        (f"XP: {xp}  (Lv {xp_level})", WHITE),
        (weapon_text,                   WHITE),
    ]
    right_lines = [
        (f"MODE: {mode_label}",              mode_color),
        (f"Episode: {episode}",              WHITE),
        (f"Ep Reward: {episode_reward:.1f}", WHITE),
        (f"Epsilon:   {epsilon:.3f}",        WHITE),
    ]
    for i, (text, color) in enumerate(left_lines):
        surface.blit(font.render(text, True, color), (8, 8 + i * 22))
    for i, (text, color) in enumerate(right_lines):
        s = font.render(text, True, color)
        surface.blit(s, (sw - s.get_width() - 8, 8 + i * 22))
    if boss_alive:
        wf = pygame.font.SysFont(None, 36)
        bw = wf.render("!! BOSS ACTIVE !!", True, PURPLE)
        surface.blit(bw, (sw // 2 - bw.get_width() // 2, 8))

def draw_fast_button(surface, fast_mode):
    sw, sh = surface.get_size()
    font   = pygame.font.SysFont(None, 24)
    label  = ">> FAST  [F]" if not fast_mode else "|| SLOW  [F]"
    color  = ORANGE if not fast_mode else DIM_GREEN
    bw, bh = 160, 36
    bx, by = sw - bw - 8, sh - bh - 8
    pygame.draw.rect(surface, color, (bx, by, bw, bh), border_radius=6)
    pygame.draw.rect(surface, WHITE, (bx, by, bw, bh), 2, border_radius=6)
    txt = font.render(label, True, BLACK)
    surface.blit(txt, (bx + (bw - txt.get_width()) // 2,
                        by + (bh - txt.get_height()) // 2))
    return pygame.Rect(bx, by, bw, bh)

# ---------------------------------------------------------------------------
# Results screen (scrollable, re-renders on resize)
# ---------------------------------------------------------------------------
def render_results_surface(reward_history, sw, tracker=None):
    """Render the full training results to an off-screen surface."""
    content_h = 1200
    if tracker:
        hist = tracker.gems_at_death_histogram()
        content_h += min(len(hist), 12) * 16
        content_h += len(tracker.choice_summary()) * 18 + 80
    surf = pygame.Surface((sw, content_h))
    surf.fill((10, 10, 20))

    fb  = pygame.font.SysFont(None, 44)
    fm  = pygame.font.SysFont(None, 28)
    fs  = pygame.font.SysFont(None, 22)
    fxs = pygame.font.SysFont(None, 19)

    title = fb.render("TRAINING COMPLETE", True, YELLOW)
    surf.blit(title, (sw // 2 - title.get_width() // 2, 10))

    total   = len(reward_history)
    avg_all = sum(reward_history) / max(total, 1)
    first50 = sum(reward_history[:50])  / 50 if total >= 50 else 0
    last50  = sum(reward_history[-50:]) / 50 if total >= 50 else 0
    best    = max(reward_history)
    worst   = min(reward_history)

    left = [
        (f"Episodes:       {total}",             WHITE),
        (f"Avg (all):      {avg_all:.1f}",       WHITE),
        (f"Avg (first 50): {first50:.1f}",       WHITE),
        (f"Avg (last 50):  {last50:.1f}",        WHITE),
        (f"Best:           {best:.1f}",          GOLD),
        (f"Worst:          {worst:.1f}",         WHITE),
        (f"Improvement:    {last50-first50:+.1f}",
         GREEN if last50 > first50 else RED),
    ]
    for i, (text, color) in enumerate(left):
        surf.blit(fm.render(text, True, color), (12, 52 + i * 26))

    if tracker:
        right = [
            (f"Win Rate:       {tracker.win_rate()*100:.1f}%",
             GREEN if tracker.win_rate() > 0.1 else WHITE),
            (f"Total Wins:     {tracker.wins}",              WHITE),
            (f"Boss Wins:      {tracker.boss_win_count()}",  PURPLE),
            (f"Boss Kills:     {tracker.boss_kills_total}",  PURPLE),
            (f"Max Plyr Level: {tracker.max_player_level}",  CYAN),
            (f"Avg Plyr Level: {tracker.avg_player_level():.1f}", CYAN),
        ]
        for i, (text, color) in enumerate(right):
            s = fm.render(text, True, color)
            surf.blit(s, (sw - s.get_width() - 12, 52 + i * 26))

    # -- Diagnostics --------------------------------------------------------
    dy = 52 + 7 * 26 + 8
    if tracker:
        pygame.draw.line(surf, GREY, (8, dy - 4), (sw - 8, dy - 4), 1)
        surf.blit(fs.render("DIAGNOSTICS", True, GOLD), (8, dy))
        dy += 22

        approach_pct   = tracker.gem_approach_ratio() * 100
        approach_color = GREEN if approach_pct > 60 else (YELLOW if approach_pct > 50 else RED)
        pct5        = tracker.pct_reaching_n_gems(5) * 100
        explore_pct = tracker.avg_tiles_revealed() / max(TOTAL_WALKABLE, 1) * 100

        diag_left = [
            (f"Avg Ticks Survived: {tracker.avg_ticks():.0f}",     WHITE),
            (f"Avg Gems Collected: {tracker.avg_gems():.1f}",      WHITE),
            (f"Reach 5 Gems:       {pct5:.1f}%",
             GREEN if pct5 > 10 else WHITE),
            (f"Avg Map Explored:   {explore_pct:.0f}%",
             GREEN if explore_pct > 30 else WHITE),
        ]
        diag_right = [
            (f"Avg Hits Taken:  {tracker.avg_hits_taken():.1f}",   WHITE),
            (f"Avg Dmg Taken:   {tracker.avg_damage_taken():.0f}", WHITE),
            (f"Gem Approach %:  {approach_pct:.0f}%",              approach_color),
        ]
        for i, (text, color) in enumerate(diag_left):
            surf.blit(fs.render(text, True, color), (12, dy + i * 20))
        for i, (text, color) in enumerate(diag_right):
            s = fs.render(text, True, color)
            surf.blit(s, (sw - s.get_width() - 12, dy + i * 20))

        dy += max(len(diag_left), len(diag_right)) * 20 + 4

        # Gem histogram
        hist = tracker.gems_at_death_histogram()
        if hist:
            surf.blit(fxs.render("Gems collected distribution:", True, GREY), (12, dy))
            dy += 16
            max_count = max(c for _, c in hist)
            bar_area  = sw - 24
            for g_count, count in hist[:12]:
                pct_bar = count / max_count
                bar_w   = max(int(pct_bar * (bar_area - 80)), 1)
                label   = fxs.render(f"{g_count:2d}:", True, CYAN)
                surf.blit(label, (12, dy))
                pygame.draw.rect(surf, CYAN, (40, dy + 2, bar_w, 12))
                ct_label = fxs.render(f"{count}", True, GREY)
                surf.blit(ct_label, (44 + bar_w, dy))
                dy += 16
            dy += 4

        pygame.draw.line(surf, GREY, (8, dy), (sw - 8, dy), 1)
        dy += 4

    # -- Weapon table -------------------------------------------------------
    if tracker:
        WEAPON_NAMES = {
            "wand": "Magic Wand", "axe": "Axe",
            "whip": "Whip", "books": "Spell Books", "shield": "Shield"
        }
        keys = tracker.all_weapon_keys()
        ty   = dy
        pygame.draw.line(surf, GREY, (8, ty - 4), (sw - 8, ty - 4), 1)
        headers  = ["Weapon", "Apps", "DPS", "Max DPS",
                    "Win%", "Avg Lv", "HP Saved"]
        n_cols   = len(headers)
        col_pad  = 12
        col_span = (sw - 2 * col_pad) / n_cols
        col_x    = [int(col_pad + i * col_span) for i in range(n_cols)]
        for cx, h in zip(col_x, headers):
            surf.blit(fs.render(h, True, GOLD), (cx, ty))
        pygame.draw.line(surf, GREY, (8, ty + 18), (sw - 8, ty + 18), 1)
        for row, key in enumerate(keys):
            ry   = ty + 24 + row * 22
            name = WEAPON_NAMES.get(key, key)
            vals = [
                name,
                str(tracker.weapon_appearances(key)),
                f"{tracker.weapon_avg_dps(key):.2f}",
                f"{tracker.weapon_max_dps(key):.2f}",
                f"{tracker.weapon_win_rate(key)*100:.1f}%",
                f"{tracker.weapon_avg_level(key):.1f}",
                f"{tracker.weapon_avg_hp_saved(key):.1f}",
            ]
            row_color = CYAN if row % 2 == 0 else WHITE
            for cx, v in zip(col_x, vals):
                surf.blit(fxs.render(v, True, row_color), (cx, ry))
        dy = ty + 24 + len(keys) * 22 + 6
        pygame.draw.line(surf, GREY, (8, dy), (sw - 8, dy), 1)

    # -- Weapon choice diagnostics ------------------------------------------
    if tracker and tracker.total_levelups() > 0:
        dy += 6
        surf.blit(fs.render(
            f"WEAPON CHOICES  ({tracker.total_levelups()} level-ups)",
            True, GOLD), (8, dy))
        dy += 22
        ch_headers = ["Weapon", "Offered", "Picked", "New", "Upgr", "Pick%", "Avg Wt"]
        n_ch    = len(ch_headers)
        ch_pad  = 12
        ch_span = (sw - 2 * ch_pad) / n_ch
        ch_col_x = [int(ch_pad + i * ch_span) for i in range(n_ch)]
        for cx, h in zip(ch_col_x, ch_headers):
            surf.blit(fxs.render(h, True, GOLD), (cx, dy))
        dy += 18
        pygame.draw.line(surf, GREY, (8, dy - 2), (sw - 8, dy - 2), 1)
        WEAPON_NAMES_C = {
            "wand": "Magic Wand", "axe": "Axe",
            "whip": "Whip", "books": "Spell Books", "shield": "Shield"
        }
        for i, entry in enumerate(tracker.choice_summary()):
            name     = WEAPON_NAMES_C.get(entry["key"], entry["key"])
            pick_pct = (entry["picked_total"] / max(entry["offered"], 1)) * 100
            vals = [
                name,
                str(entry["offered"]),
                str(entry["picked_total"]),
                str(entry["picked_new"]),
                str(entry["picked_upgrade"]),
                f"{pick_pct:.1f}%",
                f"{entry['avg_weight']:.3f}",
            ]
            row_color = CYAN if i % 2 == 0 else WHITE
            for cx, v in zip(ch_col_x, vals):
                surf.blit(fxs.render(v, True, row_color), (cx, dy))
            dy += 18
        dy += 4
        pygame.draw.line(surf, GREY, (8, dy), (sw - 8, dy), 1)

    dy += 8

    # -- Reward curve -------------------------------------------------------
    cx, cy = 10, dy
    cw     = sw - 20
    ch     = 200
    if total > 1:
        pygame.draw.rect(surf, DARK_GREY, (cx, cy, cw, ch))
        pygame.draw.rect(surf, GREY,      (cx, cy, cw, ch), 1)
        mn, mx = min(reward_history), max(reward_history)
        rng    = mx - mn if mx != mn else 1
        pts    = []
        for i, r in enumerate(reward_history):
            px = cx + int(i / (total - 1) * cw)
            py = cy + ch - int((r - mn) / rng * ch)
            pts.append((px, py))
        if len(pts) > 1:
            pygame.draw.lines(surf, CYAN, False, pts, 1)
        surf.blit(fxs.render("Ep 1", True, GREY), (cx + 2, cy + ch - 14))
        lr = fxs.render(f"Ep {total}", True, GREY)
        surf.blit(lr, (cx + cw - lr.get_width() - 2, cy + ch - 14))
    dy = cy + ch + 8

    hint = fxs.render(
        "Saved reward_history.json + run_stats.json  --  Scroll Up/Down  --  ESC to quit",
        True, GREY)
    surf.blit(hint, (sw // 2 - hint.get_width() // 2, dy))
    dy += 20

    # Trim surface to actual content height
    final = pygame.Surface((sw, dy))
    final.blit(surf, (0, 0))
    return final


def show_results_screen(screen, reward_history, tracker=None):
    """Display the scrollable results screen. Returns on ESC or quit."""
    global SCREEN_W, SCREEN_H
    results_surf = render_results_surface(reward_history, SCREEN_W, tracker)
    scroll_y     = 0
    max_scroll   = max(0, results_surf.get_height() - SCREEN_H)
    needs_rerender = False

    while True:
        for event in pygame.event.get():
            if (event.type == pygame.QUIT or
               (event.type == pygame.KEYDOWN
                and event.key == pygame.K_ESCAPE)):
                return
            elif event.type == pygame.VIDEORESIZE:
                SCREEN_W = max(event.w, 600)
                SCREEN_H = max(event.h, 400)
                screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H), pygame.RESIZABLE)
                needs_rerender = True
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 30
                scroll_y = max(0, min(scroll_y, max_scroll))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    scroll_y = max(0, scroll_y - 30)
                elif event.key == pygame.K_DOWN:
                    scroll_y = min(max_scroll, scroll_y + 30)

        if needs_rerender:
            results_surf = render_results_surface(reward_history, SCREEN_W, tracker)
            max_scroll   = max(0, results_surf.get_height() - SCREEN_H)
            scroll_y     = min(scroll_y, max_scroll)
            needs_rerender = False

        screen.fill((10, 10, 20))
        screen.blit(results_surf, (0, -scroll_y))

        if max_scroll > 0:
            sh    = SCREEN_H
            bar_h = max(20, int(sh * sh / results_surf.get_height()))
            bar_y = int(scroll_y / max_scroll * (sh - bar_h))
            pygame.draw.rect(screen, GREY,
                             (SCREEN_W - 8, bar_y, 6, bar_h),
                             border_radius=3)

        pygame.display.flip()

# ---------------------------------------------------------------------------
# Game state initialization
# ---------------------------------------------------------------------------
def make_initial_state():
    agent         = Agent(10, 10)
    w_key, w_data = get_random_starting_weapon()
    weapons       = {w_key: w_data}
    enemies       = spawn_enemies(3, COLS, ROWS, agent, MAP)
    exclude       = [(agent.x, agent.y)] + [(e.x, e.y) for e in enemies]
    gems          = spawn_gems(8, COLS, ROWS, MAP, exclude)
    return agent, weapons, enemies, gems

def reset_episode():
    agent, weapons, enemies, gems = make_initial_state()
    seen_tiles = set()
    update_seen_tiles(agent, seen_tiles)
    return agent, weapons, enemies, gems, 1, 0, 0, 1, 0, 0, [], seen_tiles

# ---------------------------------------------------------------------------
# Core simulation tick
# ---------------------------------------------------------------------------
def run_tick(agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, action,
             seen_tiles,
             ep_stats=None):

    dx, dy  = action
    prev_hp = agent.hp
    prev_xp = xp

    prev_gem_dist = min(
        (abs(agent.x - g[0]) + abs(agent.y - g[1]) for g in gems), default=0)

    # Agent moves every AGENT_MOVE_EVERY ticks (two tiles at a time)
    agent_move_timer += 1
    if agent_move_timer >= AGENT_MOVE_EVERY:
        agent_move_timer = 0
        agent.move(dx, dy)
        agent.move(dx, dy)

    curr_gem_dist = min(
        (abs(agent.x - g[0]) + abs(agent.y - g[1]) for g in gems), default=0)

    # Record move quality for diagnostics
    if agent_move_timer == 0 and ep_stats and gems:
        if curr_gem_dist < prev_gem_dist:
            ep_stats.record_move(True)
        elif curr_gem_dist > prev_gem_dist:
            ep_stats.record_move(False)
        else:
            ep_stats.record_move(None)

    # Exploration: count newly revealed tiles
    new_tiles = update_seen_tiles(agent, seen_tiles)
    if ep_stats:
        ep_stats.tiles_revealed = len(seen_tiles)

    tick_count   += 1
    episode_done  = False
    level_up      = False
    boss_win      = False

    # Enemy movement and contact damage (every other tick)
    if tick_count % 2 == 0:
        for e in enemies:
            e.step_toward_agent(agent, MAP)
        for e in list(enemies):
            if e.x == agent.x and e.y == agent.y:
                blocked = try_block_with_shield(agent, weapons, e, ep_stats)
                if not blocked:
                    agent.hp -= e.damage
                    if ep_stats:
                        ep_stats.record_hit(e.damage)
                if agent.hp <= 0:
                    episode_done = True
                    break

    # Process all weapon attacks
    orbit_positions = []
    tick_nk = tick_bk = 0

    for key, weapon in weapons.items():
        if weapon["type"] == "target":
            nk, bk = handle_wand(agent, weapon, enemies, gems,
                                  tick_count, ep_stats, key)
            tick_nk += nk; tick_bk += bk
        elif weapon["type"] == "arc":
            handle_axe(agent, weapon, active_projectiles)
        elif weapon["type"] == "directional":
            nk, bk = handle_whip(agent, weapon, enemies, gems,
                                  ep_stats, key)
            tick_nk += nk; tick_bk += bk
        elif weapon["type"] == "orbit":
            nk, bk, orbit_positions = handle_books(agent, weapon,
                                                    enemies, gems,
                                                    ep_stats, key)
            tick_nk += nk; tick_bk += bk

    pnk, pbk = update_projectiles(active_projectiles, enemies, gems,
                                   ep_stats)
    tick_nk += pnk; tick_bk += pbk

    if ep_stats and tick_bk > 0:
        ep_stats.boss_kills += tick_bk

    # Boss kill triggers an automatic win
    if tick_bk > 0:
        boss_win     = True
        episode_done = True

    kills     += tick_nk + tick_bk
    enemies[:] = [e for e in enemies if e.alive]

    # Gem collection and XP / level-up
    for gem in list(gems):
        if agent.x == gem[0] and agent.y == gem[1]:
            gems.remove(gem)
            xp += 1
            if ep_stats:
                ep_stats.record_gem()
            if xp % 5 == 0:
                xp_level += 1
                level_up = True
            if len(gems) < 4:
                excl = ([(agent.x, agent.y)]
                        + [(e.x, e.y) for e in enemies] + gems)
                gems += spawn_gems(3, COLS, ROWS, MAP, excl)

    # Spawn next wave if all enemies are dead
    if len(enemies) == 0:
        wave   += 1
        enemies = spawn_enemies(5 + wave * 2, COLS, ROWS, agent, MAP)
        if wave in BOSS_WAVES:
            boss = spawn_boss(agent, MAP, COLS, ROWS)
            if boss:
                enemies.append(boss)

    if tick_count >= MAX_TICKS:
        episode_done = True

    # -- Reward computation -------------------------------------------------
    reward = 0.0

    # Exploration: small reward for seeing new tiles
    if new_tiles > 0:
        reward += 0.3 * new_tiles

    # Gem approach: only when gem is visible (within FOG_RADIUS)
    # This teaches "when you see a gem, go get it" without
    # punishing long-distance wall navigation
    if gems and agent_move_timer == 0:
        nearest_gem_dist = min(
            abs(agent.x - g[0]) + abs(agent.y - g[1]) for g in gems)
        if nearest_gem_dist <= FOG_RADIUS:
            if curr_gem_dist < prev_gem_dist:
                reward += 5.0
            elif curr_gem_dist > prev_gem_dist:
                reward -= 2.0

    # Gem collection -- boosted to dominate damage signal
    gem_collected = xp - prev_xp
    if gem_collected > 0:
        reward += 30.0 * gem_collected

    # Level-up bonus
    if level_up:
        reward += 50.0

    # Kill reward (small -- agent does not directly control weapons)
    reward += tick_nk * 1.0

    # Damage penalty (scaled by amount)
    hp_lost = prev_hp - agent.hp
    if hp_lost > 0:
        reward -= 2.0 * (hp_lost / 5.0)

    # Terminal rewards
    if boss_win:
        remaining_ratio = (MAX_TICKS - tick_count) / MAX_TICKS
        reward = 100.0 + remaining_ratio * 200.0
    elif episode_done and agent.hp <= 0:
        early_mult = 1.0 + (MAX_TICKS - tick_count) / MAX_TICKS
        reward = -30.0 * early_mult
    elif episode_done:
        reward += 50.0

    boss_alive = any(e.symbol == "B" for e in enemies)

    return (agent, weapons, enemies, gems,
            wave, kills, xp, xp_level,
            tick_count, agent_move_timer,
            active_projectiles, seen_tiles, reward,
            episode_done, orbit_positions,
            boss_alive, level_up, boss_win)

# ---------------------------------------------------------------------------
# Headless fast training
# ---------------------------------------------------------------------------
def run_fast_training(rl, weapon_rl, reward_history, start_episode):
    tracker = RunTracker()
    episode = start_episode
    print(f"\n[FAST] Starting training from episode {episode} ...")

    while episode < MAX_EPISODES:
        (agent, weapons, enemies, gems,
         wave, kills, xp, xp_level,
         tick_count, agent_move_timer,
         active_projectiles, seen_tiles) = reset_episode()
        episode_reward = 0.0
        ep_stats       = tracker.start_episode()

        state  = rl.get_state(agent, enemies, gems, weapons, xp)
        action = rl.choose_action(state)
        accum_reward = 0.0

        while True:
            (agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, seen_tiles, reward,
             done, _, _, level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems,
                wave, kills, xp, xp_level,
                tick_count, agent_move_timer,
                active_projectiles, action,
                seen_tiles,
                ep_stats=ep_stats)

            accum_reward   += reward
            episode_reward += reward

            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    w_state = weapon_rl.get_state(agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_state, len(choices))
                    weapon_rl.record_choice(w_state, idx)
                    # Record Q-values as weights for diagnostics
                    q_weights = [weapon_rl.get_q(w_state, i) for i in range(len(choices))]
                    if ep_stats:
                        ep_stats.weapon_choices.append((choices, q_weights, idx))
                    apply_choice(choices[idx], weapons)

            ep_stats.ticks        = tick_count
            ep_stats.player_level = xp_level
            ep_stats.record_weapon_state(weapons)

            # Q-update only on actual movement ticks or episode end
            moved = (agent_move_timer == 0)
            if moved or done:
                next_state = rl.get_state(agent, enemies, gems, weapons, xp)
                rl.update(state, action, accum_reward, next_state)
                accum_reward = 0.0

                if done:
                    won = boss_win or (tick_count >= MAX_TICKS)
                    if boss_win:
                        ep_stats.boss_win = True

                    # Update weapon Q-agent with episode outcome
                    weapon_rl.update(episode_reward)

                    tracker.end_episode(won=won)
                    break

                state  = next_state
                action = rl.choose_action(state)

        reward_history.append(episode_reward)
        episode += 1

        if episode % 100 == 0:
            avg = sum(reward_history[-100:]) / 100
            wr  = tracker.win_rate() * 100
            print(f"  Ep {episode:5d} | Avg(100): {avg:8.2f} | "
                  f"WinRate: {wr:.1f}% | eps:{rl.epsilon:.3f}")

        if episode % 1000 == 0 and episode > 0:
            print(f"\n  --- Diagnostics at ep {episode} ---")
            print(f"    Avg Ticks:  {tracker.avg_ticks():.0f}")
            print(f"    Avg Gems:   {tracker.avg_gems():.1f}")
            print(f"    Avg Hits:   {tracker.avg_hits_taken():.1f}")
            print(f"    Avg Dmg:    {tracker.avg_damage_taken():.0f}")
            print(f"    Gem-> ratio: {tracker.gem_approach_ratio()*100:.0f}%")
            print(f"    >=5 gems:    {tracker.pct_reaching_n_gems(5)*100:.1f}%")
            print(f"    Map seen:   {tracker.avg_tiles_revealed()/TOTAL_WALKABLE*100:.0f}%")
            print(f"    Boss wins:  {tracker.boss_win_count()}")
            print(f"    Level-ups:  {tracker.total_levelups()}")
            cs = tracker.choice_summary()
            if cs:
                print("    Weapon choices:")
                for e in cs:
                    pct = (e['picked_total'] / max(e['offered'], 1)) * 100
                    print(f"      {e['key']:10s}  offered:{e['offered']:5d}  "
                          f"picked:{e['picked_total']:4d} ({pct:4.1f}%)  "
                          f"avg_wt:{e['avg_weight']:.3f}")
            print("\n  Weapon stats:")
            for key in ["wand", "axe", "whip", "books"]:
                wr   = tracker.weapon_win_rate(key) * 100
                adps = tracker.weapon_avg_dps(key)
                saved = tracker.weapon_avg_hp_saved(key)
                print(f"    {key:10s}  WR:{wr:.1f}%  DPS:{adps:.2f}  HP Saved:{saved:.2f}")
            print()

    print(f"\n[DONE] {episode} episodes completed | Wins: {tracker.wins}")
    with open("reward_history.json", "w") as f:
        json.dump(reward_history, f)
    with open("run_stats.json", "w") as f:
        json.dump(tracker.summary_dict(), f, indent=2)
    print("   Saved reward_history.json + run_stats.json")
    return episode, tracker

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    global TRAINING, FAST_MODE, SCREEN_W, SCREEN_H

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Vampire Survivors RL -- Capstone")
    clock     = pygame.time.Clock()
    tile_font = pygame.font.SysFont(None, 22)

    # Off-screen surface for the game map (always 480x480)
    game_surface = pygame.Surface((W, H))

    # Load sprites (fall back to shapes if assets are missing)
    spr_player = load_sprite("player.png")
    spr_enemy  = load_sprite("enemy.png")
    spr_boss   = load_sprite("boss.png")
    spr_gem    = load_sprite("gem.png")

    ACTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)]
    rl      = QLearningAgent(actions=ACTIONS, game_map=MAP)
    weapon_rl = WeaponChoiceAgent()

    episode        = 0
    episode_reward = 0.0
    reward_history = []
    last_tracker   = None
    tracker        = RunTracker()
    ep_stats       = tracker.start_episode()

    (agent, weapons, enemies, gems,
     wave, kills, xp, xp_level,
     tick_count, agent_move_timer,
     active_projectiles, seen_tiles) = reset_episode()

    orbit_positions = []
    boss_alive      = False
    training_done   = False
    running         = True

    # Persistent RL decision state across frames
    rl_state  = rl.get_state(agent, enemies, gems, weapons, xp)
    rl_action = rl.choose_action(rl_state)
    rl_accum  = 0.0

    while running:
        clock.tick(FPS)
        btn_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                SCREEN_W = max(event.w, W + 40)
                SCREEN_H = max(event.h, H + 40)
                screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_t:      TRAINING = not TRAINING
                if event.key == pygame.K_f:
                    FAST_MODE = not FAST_MODE
                    if FAST_MODE and TRAINING:
                        episode, last_tracker = run_fast_training(
                            rl, weapon_rl, reward_history, episode)
                        FAST_MODE     = False
                        training_done = True
                if not TRAINING:
                    if event.key == pygame.K_UP:
                        agent.move(0, -1); agent.move(0, -1)
                    if event.key == pygame.K_DOWN:
                        agent.move(0, 1);  agent.move(0, 1)
                    if event.key == pygame.K_LEFT:
                        agent.move(-1, 0); agent.move(-1, 0)
                    if event.key == pygame.K_RIGHT:
                        agent.move(1, 0);  agent.move(1, 0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect and btn_rect.collidepoint(event.pos):
                    FAST_MODE = not FAST_MODE
                    if FAST_MODE and TRAINING:
                        episode, last_tracker = run_fast_training(
                            rl, weapon_rl, reward_history, episode)
                        FAST_MODE     = False
                        training_done = True

        if training_done:
            show_results_screen(screen, reward_history, last_tracker)
            training_done = False
            running = False
            continue

        episode_done = False
        level_up     = False
        boss_win     = False

        if TRAINING:
            (agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, seen_tiles, reward,
             episode_done, orbit_positions,
             boss_alive, level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems,
                wave, kills, xp, xp_level,
                tick_count, agent_move_timer,
                active_projectiles, rl_action,
                seen_tiles,
                ep_stats=ep_stats)

            rl_accum       += reward
            episode_reward += reward

            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    w_state = weapon_rl.get_state(agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_state, len(choices))
                    weapon_rl.record_choice(w_state, idx)
                    q_weights = [weapon_rl.get_q(w_state, i) for i in range(len(choices))]
                    if ep_stats:
                        ep_stats.weapon_choices.append((choices, q_weights, idx))
                    apply_choice(choices[idx], weapons)

            ep_stats.ticks        = tick_count
            ep_stats.player_level = xp_level
            ep_stats.record_weapon_state(weapons)

            moved = (agent_move_timer == 0)
            if moved or episode_done:
                next_state = rl.get_state(agent, enemies, gems, weapons, xp)
                rl.update(rl_state, rl_action, rl_accum, next_state)
                rl_accum  = 0.0
                rl_state  = next_state
                rl_action = rl.choose_action(rl_state)

        else:
            # Manual play mode
            tick_count += 1
            orbit_positions = []
            update_seen_tiles(agent, seen_tiles)
            if tick_count % 2 == 0:
                for e in enemies:
                    e.step_toward_agent(agent, MAP)
                for e in list(enemies):
                    if e.x == agent.x and e.y == agent.y:
                        blocked = try_block_with_shield(agent, weapons, e, None)
                        if not blocked:
                            agent.hp -= e.damage
                        if agent.hp <= 0:
                            episode_done = True
                            break
            for key, weapon in weapons.items():
                if weapon["type"] == "target":
                    handle_wand(agent, weapon, enemies, gems, tick_count)
                elif weapon["type"] == "arc":
                    handle_axe(agent, weapon, active_projectiles)
                elif weapon["type"] == "directional":
                    handle_whip(agent, weapon, enemies, gems)
                elif weapon["type"] == "orbit":
                    _, _, orbit_positions = handle_books(
                        agent, weapon, enemies, gems)
            update_projectiles(active_projectiles, enemies, gems)
            enemies[:] = [e for e in enemies if e.alive]
            for gem in list(gems):
                if agent.x == gem[0] and agent.y == gem[1]:
                    gems.remove(gem)
                    xp += 1
                    if xp % 5 == 0:
                        xp_level += 1
                        level_up = True
            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    idx = run_level_up_ui(screen, choices, weapons)
                    apply_choice(choices[idx], weapons)
            if len(enemies) == 0:
                wave   += 1
                enemies = spawn_enemies(5 + wave * 2, COLS, ROWS, agent, MAP)
                if wave in BOSS_WAVES:
                    boss = spawn_boss(agent, MAP, COLS, ROWS)
                    if boss:
                        enemies.append(boss)
            boss_alive = any(e.symbol == "B" for e in enemies)

        # Episode end handling (training mode)
        if episode_done and TRAINING:
            reward_history.append(episode_reward)
            episode += 1

            won = boss_win or (tick_count >= MAX_TICKS)
            if boss_win and ep_stats:
                ep_stats.boss_win = True

            # Update weapon Q-agent with episode outcome
            weapon_rl.update(episode_reward)

            tracker.end_episode(won=won)
            last_tracker = tracker

            episode_reward = 0.0

            if episode >= MAX_EPISODES:
                with open("reward_history.json", "w") as f:
                    json.dump(reward_history, f)
                with open("run_stats.json", "w") as f:
                    json.dump(tracker.summary_dict(), f, indent=2)
                training_done = True

            (agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, seen_tiles) = reset_episode()
            boss_alive = False
            ep_stats = tracker.start_episode()

            rl_state  = rl.get_state(agent, enemies, gems, weapons, xp)
            rl_action = rl.choose_action(rl_state)
            rl_accum  = 0.0

            if episode % 50 == 0:
                avg = sum(reward_history[-50:]) / 50
                print(f"Ep {episode:4d} | Avg(50): {avg:7.2f} | "
                      f"eps:{rl.epsilon:.3f}")

        # -- Draw -----------------------------------------------------------
        game_surface.fill(BLACK)
        draw_map(game_surface)

        for gx, gy in gems:
            if spr_gem:
                game_surface.blit(spr_gem, (gx * TILE, gy * TILE))
            else:
                rect = pygame.Rect(gx * TILE, gy * TILE, TILE, TILE)
                pygame.draw.rect(game_surface, YELLOW, rect)
                game_surface.blit(tile_font.render("*", True, BLACK),
                                  (gx * TILE + 7, gy * TILE + 4))

        for ox, oy in orbit_positions:
            if 0 <= ox < COLS and 0 <= oy < ROWS:
                pygame.draw.rect(game_surface, BLUE,
                                 pygame.Rect(ox * TILE, oy * TILE, TILE, TILE))

        draw_projectiles(game_surface, active_projectiles)

        if any(w["type"] == "defense" for w in weapons.values()):
            fx, fy = agent.facing
            sx, sy = agent.x + fx, agent.y + fy
            if 0 <= sx < COLS and 0 <= sy < ROWS:
                pygame.draw.rect(game_surface, CYAN,
                                 pygame.Rect(sx * TILE, sy * TILE, TILE, TILE), 3)

        for e in enemies:
            if e.alive:
                if e.symbol == "B" and spr_boss:
                    game_surface.blit(spr_boss, (e.x * TILE, e.y * TILE))
                elif e.symbol != "B" and spr_enemy:
                    game_surface.blit(spr_enemy, (e.x * TILE, e.y * TILE))
                else:
                    e.draw(game_surface, TILE, tile_font)

        if spr_player:
            game_surface.blit(spr_player, (agent.x * TILE, agent.y * TILE))
        else:
            agent.draw(game_surface, tile_font)
        draw_fog(game_surface, agent)

        # Compose: game surface centered on main screen
        screen.fill(BLACK)
        map_x = (SCREEN_W - W) // 2
        map_y = (SCREEN_H - H) // 2
        screen.blit(game_surface, (map_x, map_y))

        # HUD and controls on main screen
        draw_hud(screen, agent, wave, kills, xp, xp_level,
                 weapons, episode, episode_reward, rl.epsilon,
                 FAST_MODE, boss_alive)
        btn_rect = draw_fast_button(screen, FAST_MODE)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()