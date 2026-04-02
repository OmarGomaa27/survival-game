import pygame
from game.config import COLS, ROWS, MAP, TILE, GREEN, WHITE


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
        rect = pygame.Rect(self.x * TILE, self.y * TILE, TILE, TILE)
        pygame.draw.rect(surface, GREEN, rect)
        label = font.render("@", True, WHITE)
        surface.blit(label, (self.x * TILE + 8, self.y * TILE + 6))
