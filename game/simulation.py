import random
from game.config import (FOG_RADIUS, ROWS, COLS, MAP, AGENT_MOVE_EVERY,
                         BOSS_SPAWN_TICK, MAX_TICKS, FPS)
from game.agent import Agent
from game.enemy import spawn_enemies
from game.weapons import get_random_starting_weapon
from game.gems import spawn_gems, spawn_boss, nearest_gem_dist
from game.weapon_handlers import (handle_wand, handle_axe, handle_whip,
                                  handle_books, update_projectiles,
                                  try_block_with_shield)

_seen_last_pos = [None, None]


def update_seen_tiles(agent, seen_tiles):
    if _seen_last_pos[0] == agent.x and _seen_last_pos[1] == agent.y:
        return 0
    _seen_last_pos[0], _seen_last_pos[1] = agent.x, agent.y
    new_count = 0
    r = FOG_RADIUS
    r_sq = r * r
    ax, ay = agent.x, agent.y
    min_row = max(0, ay - r)
    max_row = min(ROWS - 1, ay + r)
    min_col = max(0, ax - r)
    max_col = min(COLS - 1, ax + r)
    for row in range(min_row, max_row + 1):
        dy = row - ay
        dy_sq = dy * dy
        for col in range(min_col, max_col + 1):
            if (col, row) not in seen_tiles:
                dx = col - ax
                if dx * dx + dy_sq <= r_sq:
                    seen_tiles.add((col, row))
                    new_count += 1
    return new_count


def make_initial_state():
    agent         = Agent(10, 10)
    w_key, w_data = get_random_starting_weapon()
    weapons       = {w_key: w_data}
    enemies       = spawn_enemies(3, COLS, ROWS, agent, MAP)
    exclude       = [(agent.x, agent.y)] + [(e.x, e.y) for e in enemies]
    gems          = spawn_gems(8, COLS, ROWS, MAP, exclude)
    return agent, weapons, enemies, gems


def reset_episode():
    global _seen_last_pos
    _seen_last_pos[0], _seen_last_pos[1] = None, None
    agent, weapons, enemies, gems = make_initial_state()
    seen_tiles = set()
    update_seen_tiles(agent, seen_tiles)
    return agent, weapons, enemies, gems, 1, 0, 0, 1, 0, 0, [], seen_tiles


def run_tick(agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, action,
             seen_tiles, ep_stats=None):

    dx, dy  = action
    prev_hp = agent.hp
    prev_xp = xp

    agent_move_timer += 1
    moved = agent_move_timer >= AGENT_MOVE_EVERY
    if moved:
        agent_move_timer = 0
        prev_gem_dist = nearest_gem_dist(agent.x, agent.y, gems)
        agent.move(dx, dy)
        curr_gem_dist = nearest_gem_dist(agent.x, agent.y, gems)
    else:
        prev_gem_dist = curr_gem_dist = 0

    if moved and ep_stats and gems:
        if curr_gem_dist < prev_gem_dist:
            ep_stats.record_move(True)
        elif curr_gem_dist > prev_gem_dist:
            ep_stats.record_move(False)
        else:
            ep_stats.record_move(None)

    new_tiles = update_seen_tiles(agent, seen_tiles)
    if ep_stats:
        ep_stats.tiles_revealed = len(seen_tiles)

    tick_count   += 1
    episode_done  = False
    level_up      = False
    boss_win      = False

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

    pnk, pbk = update_projectiles(active_projectiles, enemies, gems, ep_stats)
    tick_nk += pnk; tick_bk += pbk

    if ep_stats and tick_bk > 0:
        ep_stats.boss_kills += tick_bk

    if tick_bk > 0:
        boss_win     = True
        episode_done = True

    kills += tick_nk + tick_bk
    enemies[:] = [e for e in enemies if e.alive]

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

    if len(enemies) == 0:
        wave   += 1
        enemies = spawn_enemies(5 + wave * 2, COLS, ROWS, agent, MAP)

    if tick_count == BOSS_SPAWN_TICK:
        boss = spawn_boss(agent, MAP, COLS, ROWS)
        if boss:
            enemies.append(boss)

    if tick_count >= MAX_TICKS:
        episode_done = True

    # -- Reward --
    reward = 0.0
    reward += 0.05

    if new_tiles > 0:
        reward += 0.8 * new_tiles

    if moved and gems:
        if curr_gem_dist <= FOG_RADIUS:
            if curr_gem_dist < prev_gem_dist:
                reward += 5.0
            elif curr_gem_dist > prev_gem_dist:
                reward -= 2.0

    gem_collected = xp - prev_xp
    if gem_collected > 0:
        reward += 30.0 * gem_collected

    if level_up:
        reward += 50.0

    reward += tick_nk * 1.0

    hp_lost = prev_hp - agent.hp
    if hp_lost > 0:
        hp_ratio = agent.hp / 100.0
        danger_mult = 1.0 + 3.0 * (1.0 - hp_ratio)
        reward -= 2.0 * (hp_lost / 5.0) * danger_mult

    # penalize being near enemies when HP is low
    if moved and enemies:
        nearest_enemy_dist = min(
            abs(e.x - agent.x) + abs(e.y - agent.y) for e in enemies)
        if agent.hp <= 50 and nearest_enemy_dist <= 2:
            reward -= 3.0 * (1.0 - agent.hp / 100.0)

    if boss_win:
        remaining_ratio = (MAX_TICKS - tick_count) / MAX_TICKS
        reward = 100.0 + remaining_ratio * 200.0
    elif episode_done and agent.hp <= 0:
        early_mult = 1.0 + (MAX_TICKS - tick_count) / MAX_TICKS
        reward = -30.0 * early_mult
    elif episode_done:
        reward += 50.0

    if tick_count >= BOSS_SPAWN_TICK:
        boss_alive = any(e.symbol == "B" for e in enemies)
    else:
        boss_alive = False

    return (agent, weapons, enemies, gems,
            wave, kills, xp, xp_level,
            tick_count, agent_move_timer,
            active_projectiles, seen_tiles, reward,
            episode_done, orbit_positions,
            boss_alive, level_up, boss_win)