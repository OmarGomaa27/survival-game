import pygame
import game.config as config

active_effects = []


def add_effect(x, y, color, frames=3, style="fill"):
    if config.FAST_MODE:
        return
    active_effects.append({"x": x, "y": y, "color": color,
                           "frames": frames, "style": style})


def update_effects():
    for eff in active_effects:
        eff["frames"] -= 1
    active_effects[:] = [e for e in active_effects if e["frames"] > 0]


def draw_effects(surface):
    T = config.TILE
    for eff in active_effects:
        x, y = eff["x"], eff["y"]
        if not (0 <= x < config.COLS and 0 <= y < config.ROWS):
            continue
        rect = pygame.Rect(x * T + 2, y * T + 2, T - 4, T - 4)
        if eff["style"] == "fill":
            s = pygame.Surface((T - 4, T - 4), pygame.SRCALPHA)
            s.fill((*eff["color"], 160))
            surface.blit(s, (x * T + 2, y * T + 2))
        elif eff["style"] == "ring":
            pygame.draw.rect(surface, eff["color"], rect, 2, border_radius=4)
        elif eff["style"] == "cross":
            cx = x * T + T // 2
            cy = y * T + T // 2
            pygame.draw.line(surface, eff["color"],
                             (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
            pygame.draw.line(surface, eff["color"],
                             (cx + 6, cy - 6), (cx - 6, cy + 6), 2)
