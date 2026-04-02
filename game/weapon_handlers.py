import random
import math
from game.config import MAP, COLS, ROWS, BURST_INTER_DELAY
from game.gems import drop_gem, drop_boss_gems
from ui.effects import add_effect


def handle_wand(agent, weapon, enemies, gems, tick_count,
                ep_stats=None, weapon_key="wand"):
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
                add_effect(nearest.x, nearest.y, (255,255,255), frames=2, style="cross")
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
    n   = weapon.get("projectiles", 1)
    dmg = weapon["damage"]
    if n == 1:
        vx_vals = [0.5]
    else:
        vx_vals = []
        for i in range(n):
            side = -1 if i % 2 == 0 else 1
            spread = 0.3 + (i // 2) * 0.3
            vx_vals.append(side * spread)
    projs = []
    for vx in vx_vals:
        projs.append({
            "type": "axe", "x": float(agent.x), "y": float(agent.y),
            "vx": vx, "vy": -1.5, "gravity": 0.12, "damage": dmg,
            "hit_ids": set(), "alive": True,
        })
    return projs


def handle_axe(agent, weapon, active_projectiles):
    weapon["timer"] += 1
    if weapon["timer"] >= weapon["cooldown"]:
        weapon["timer"] = 0
        active_projectiles.extend(spawn_axe_volley(agent, weapon))


def update_projectiles(active_projectiles, enemies, gems, ep_stats=None):
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
            for dist in range(1, weapon["range"] + 1):
                sx = agent.x + dx * dist
                sy = agent.y + dy * dist
                add_effect(sx, sy, (255,60,60), frames=2, style="fill")
                if dx != 0:
                    add_effect(sx, agent.y - 1, (255,60,60), frames=2, style="fill")
                    add_effect(sx, agent.y + 1, (255,60,60), frames=2, style="fill")
                if dy != 0:
                    add_effect(agent.x - 1, sy, (255,60,60), frames=2, style="fill")
                    add_effect(agent.x + 1, sy, (255,60,60), frames=2, style="fill")
            for e in list(enemies):
                rx, ry = e.x - agent.x, e.y - agent.y
                in_front = (
                    (dx != 0 and rx * dx > 0 and abs(ry) <= 1) or
                    (dy != 0 and ry * dy > 0 and abs(rx) <= 1)
                )
                if in_front and abs(rx) + abs(ry) <= weapon["range"]:
                    is_boss = e.symbol == "B"
                    dmg     = weapon["damage"]
                    e.take_damage(dmg)
                    agent.hp = min(agent.hp + 3, 100)
                    add_effect(e.x, e.y, (255,80,80), frames=3, style="ring")
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
                add_effect(e.x, e.y, (100,180,255), frames=2, style="cross")
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
    for weapon in weapons.values():
        if weapon["type"] != "defense":
            continue
        dx, dy = agent.facing
        ix, iy = enemy.x - agent.x, enemy.y - agent.y
        in_front = (dx != 0 and ix * dx > 0) or (dy != 0 and iy * dy > 0)
        if in_front and random.random() < weapon["block_chance"]:
            if ep_stats:
                ep_stats.record_block("shield", enemy.damage)
            return True
    return False
