import random

RED    = (200, 50,  50)
ORANGE = (220, 120, 30)
WHITE  = (255, 255, 255)

class Enemy:
    def __init__(self, x, y, hp=20, damage=10, speed=1, color=RED, symbol="E"):
        self.x      = x
        self.y      = y
        self.hp     = hp
        self.damage = damage
        self.speed  = speed   # tiles moved per tick (1 for now)
        self.color  = color
        self.symbol = symbol
        self.alive  = True
        self._move_timer = 0  # so slow enemies skip ticks

    def step_toward_agent(self, agent, game_map):
        """Move one tile closer to agent, avoid walls."""
        self._move_timer += 1
        if self._move_timer < self.speed:
            return
        self._move_timer = 0

        dx = agent.x - self.x
        dy = agent.y - self.y

        # try to move in the dominant direction first, fallback to other
        moves = []
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
        rect = pygame.Rect(self.x*tile_size, self.y*tile_size, tile_size, tile_size)
        pygame.draw.rect(surface, self.color, rect)
        label = font.render(self.symbol, True, WHITE)
        surface.blit(label, (self.x*tile_size+8, self.y*tile_size+6))


def sign(n):
    if n > 0: return 1
    if n < 0: return -1
    return 0


def spawn_enemies(n, cols, rows, agent, min_dist=8):
    """Spawn n enemies at random positions far from the agent."""
    enemies = []
    attempts = 0
    while len(enemies) < n and attempts < 1000:
        x = random.randint(1, cols-2)
        y = random.randint(1, rows-2)
        dist = abs(x - agent.x) + abs(y - agent.y)
        if dist >= min_dist:
            enemies.append(Enemy(x, y))
        attempts += 1
    return enemies