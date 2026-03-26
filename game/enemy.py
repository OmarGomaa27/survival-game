import random

RED    = (200, 50,  50)
ORANGE = (220, 120, 30)
PURPLE = (160, 30,  200)
WHITE  = (255, 255, 255)
YELLOW = (255, 220, 0)


def sign(n):
    if n > 0: return 1
    if n < 0: return -1
    return 0


class Enemy:
    def __init__(self, x, y, hp=20, damage=5, speed=1,
                 color=RED, symbol="E"):
        self.x            = x
        self.y            = y
        self.hp           = hp
        self.max_hp       = hp
        self.damage       = damage
        self.speed        = speed
        self.color        = color
        self.symbol       = symbol
        self.alive        = True
        self._move_timer  = 0
        self.is_boss      = False

    def step_toward_agent(self, agent, game_map):
        self._move_timer += 1
        if self._move_timer < self.speed:
            return
        self._move_timer = 0

        dx = agent.x - self.x
        dy = agent.y - self.y

        if abs(dx) >= abs(dy):
            moves = [(sign(dx), 0), (0, sign(dy))]
        else:
            moves = [(0, sign(dy)), (sign(dx), 0)]

        for mdx, mdy in moves:
            nx, ny = self.x + mdx, self.y + mdy
            rows = len(game_map)
            cols = len(game_map[0])
            if 0 <= nx < cols and 0 <= ny < rows and game_map[ny][nx] == 0:
                self.x, self.y = nx, ny
                break

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def draw(self, surface, tile_size, font):
        import pygame
        rect = pygame.Rect(self.x*tile_size, self.y*tile_size,
                           tile_size, tile_size)
        pygame.draw.rect(surface, self.color, rect)
        label = font.render(self.symbol, True, WHITE)
        surface.blit(label, (self.x*tile_size+6, self.y*tile_size+4))

        if self.is_boss:
            bar_w  = tile_size * 3
            bar_h  = 5
            bx     = self.x*tile_size - tile_size
            by     = self.y*tile_size - 8
            ratio  = max(self.hp / self.max_hp, 0)
            pygame.draw.rect(surface, (80, 0, 0),
                             (bx, by, bar_w, bar_h))
            pygame.draw.rect(surface, (220, 50, 220),
                             (bx, by, int(bar_w * ratio), bar_h))


class Boss(Enemy):
    def __init__(self, x, y):
        super().__init__(
            x=x, y=y,
            hp=300,
            damage=30,
            speed=2,
            color=PURPLE,
            symbol="B",
        )
        self.is_boss = True

    def drop_big_gem(self, gems):
        offsets = [
            (0,0),(1,0),(-1,0),(0,1),(0,-1),
            (1,1),(-1,1),(1,-1),(-1,-1),(2,0)
        ]
        for dx, dy in offsets:
            pos = (self.x + dx, self.y + dy)
            if pos not in gems:
                gems.append(pos)


def spawn_enemies(n, cols, rows, agent, game_map, min_dist=8):
    enemies  = []
    attempts = 0
    while len(enemies) < n and attempts < 1000:
        x = random.randint(1, cols-2)
        y = random.randint(1, rows-2)
        dist = abs(x - agent.x) + abs(y - agent.y)
        if dist >= min_dist and game_map[y][x] == 0:
            enemies.append(Enemy(x, y))
        attempts += 1
    return enemies


def spawn_boss(cols, rows, agent, game_map, min_dist=10):
    attempts = 0
    best_pos = None
    best_dist = 0
    while attempts < 500:
        x = random.randint(1, cols-2)
        y = random.randint(1, rows-2)
        if game_map[y][x] == 0:
            dist = abs(x - agent.x) + abs(y - agent.y)
            if dist >= min_dist and dist > best_dist:
                best_dist = dist
                best_pos  = (x, y)
        attempts += 1
    if best_pos:
        return Boss(best_pos[0], best_pos[1])
    return Boss(1, 1)