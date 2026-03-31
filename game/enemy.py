import random
import math

# Default colors (match main.py palette)
RED    = (200, 50, 50)
PURPLE = (180, 0, 220)
WHITE  = (255, 255, 255)


class Enemy:
    """A single enemy that chases the player agent."""

    def __init__(self, x, y, hp=30, damage=10, speed=2,
                 color=RED, symbol="E"):
        self.x      = x
        self.y      = y
        self.hp     = hp
        self.damage = damage
        self.speed  = speed   # moves every `speed` ticks in step_toward_agent
        self.color  = color
        self.symbol = symbol
        self.alive  = True
        self._step  = 0       # internal tick counter for movement pacing

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def step_toward_agent(self, agent, game_map):
        """Move one tile closer to the agent every `self.speed` calls.
        Uses simple greedy Manhattan-distance movement; ignores walls
        (enemies phase through walls like in Vampire Survivors)."""
        self._step += 1
        if self._step < self.speed:
            return
        self._step = 0

        dx = 0 if agent.x == self.x else int(math.copysign(1, agent.x - self.x))
        dy = 0 if agent.y == self.y else int(math.copysign(1, agent.y - self.y))

        rows = len(game_map)
        cols = len(game_map[0]) if rows > 0 else 0

        # Try primary axis (larger distance first), then secondary
        if abs(agent.x - self.x) >= abs(agent.y - self.y):
            axes = [(dx, 0), (0, dy)]
        else:
            axes = [(0, dy), (dx, 0)]

        for mx, my in axes:
            if mx == 0 and my == 0:
                continue
            nx, ny = self.x + mx, self.y + my
            if 0 <= nx < cols and 0 <= ny < rows:
                self.x, self.y = nx, ny
                return

        # Fallback: just move in any valid direction toward agent
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            self.x, self.y = nx, ny

    def draw(self, surface, tile_size, font):
        """Fallback primitive rendering (used when sprites are missing)."""
        import pygame
        rect = pygame.Rect(self.x * tile_size, self.y * tile_size,
                           tile_size, tile_size)
        pygame.draw.rect(surface, self.color, rect)
        label = font.render(self.symbol, True, WHITE)
        surface.blit(label, (self.x * tile_size + 6, self.y * tile_size + 4))


def spawn_enemies(count, cols, rows, agent, game_map, min_dist=5):
    """Spawn `count` enemies on walkable tiles, at least `min_dist`
    Manhattan distance from the agent."""
    enemies  = []
    attempts = 0
    while len(enemies) < count and attempts < count * 50:
        x = random.randint(1, cols - 2)
        y = random.randint(1, rows - 2)
        dist = abs(x - agent.x) + abs(y - agent.y)
        if game_map[y][x] == 0 and dist >= min_dist:
            enemies.append(Enemy(x, y))
        attempts += 1
    return enemies