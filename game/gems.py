import random
from game.config import COLS, ROWS, MAP, PURPLE
from game.enemy import Enemy


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
    offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),
               (1,1),(-1,1),(1,-1),(-1,-1),(2,0)]
    for dx, dy in offsets:
        nx, ny = enemy.x + dx, enemy.y + dy
        if (0 <= nx < COLS and 0 <= ny < ROWS
                and game_map[ny][nx] == 0
                and (nx, ny) not in gems):
            gems.append((nx, ny))


def spawn_boss(agent, game_map, cols, rows):
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


def nearest_gem_dist(ax, ay, gems):
    best = 9999
    for g in gems:
        d = abs(ax - g[0]) + abs(ay - g[1])
        if d < best:
            best = d
    return best
