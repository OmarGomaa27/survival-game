import os
import pygame
import game.config as config


def load_sprite(filename):
    path = os.path.join(config.ASSET_DIR, filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, (config.TILE, config.TILE))
    except Exception as e:
        print(f"Warning: could not load {filename}: {e}")
        return None


def draw_map(surface):
    for row in range(config.ROWS):
        for col in range(config.COLS):
            color = config.GREY if config.MAP[row][col] == 1 else config.DARK_GREY
            rect = pygame.Rect(col * config.TILE, row * config.TILE,
                               config.TILE, config.TILE)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, config.BLACK, rect, 1)


def draw_fog(surface, agent):
    fog = pygame.Surface((config.W, config.H), pygame.SRCALPHA)
    fog.fill((0, 0, 0, 240))
    for row in range(config.ROWS):
        for col in range(config.COLS):
            dist = ((col - agent.x)**2 + (row - agent.y)**2) ** 0.5
            if dist <= config.FOG_RADIUS:
                pygame.draw.rect(fog, (0, 0, 0, 0),
                                 (col * config.TILE, row * config.TILE,
                                  config.TILE, config.TILE))
    surface.blit(fog, (0, 0))


def draw_projectiles(surface, active_projectiles):
    for proj in active_projectiles:
        if not proj["alive"]:
            continue
        gx = int(round(proj["x"]))
        gy = int(round(proj["y"]))
        if 0 <= gx < config.COLS and 0 <= gy < config.ROWS:
            T = config.TILE
            rect = pygame.Rect(gx * T + 4, gy * T + 4, T - 8, T - 8)
            pygame.draw.rect(surface, config.ORANGE, rect, border_radius=3)
            pygame.draw.rect(surface, config.GOLD, rect, 1, border_radius=3)


def draw_hud(surface, agent, wave, kills, xp, xp_level,
             weapons, episode, episode_reward, epsilon,
             fast_mode, boss_alive, mode):
    sw = surface.get_width()
    font    = pygame.font.SysFont(None, 24)
    font_sm = pygame.font.SysFont(None, 20)
    y = 8

    hp_label = font.render(f"HP: {agent.hp}/100", True, config.WHITE)
    surface.blit(hp_label, (8, y))
    bar_x, bar_w, bar_h = 120, 150, 16
    hp_ratio = max(agent.hp / 100, 0)
    hp_color = config.GREEN if hp_ratio > 0.5 else (config.YELLOW if hp_ratio > 0.25 else config.RED)
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, y + 2, bar_w, bar_h))
    pygame.draw.rect(surface, hp_color, (bar_x, y + 2, int(bar_w * hp_ratio), bar_h))
    pygame.draw.rect(surface, config.WHITE, (bar_x, y + 2, bar_w, bar_h), 1)
    y += 22

    xp_in_level = xp % 5
    xp_ratio = xp_in_level / 5.0
    lv_label = font.render(f"Lv {xp_level}  ({xp_in_level}/5 XP)", True, config.WHITE)
    surface.blit(lv_label, (8, y))
    pygame.draw.rect(surface, (40, 40, 40), (bar_x + 40, y + 2, bar_w - 40, bar_h))
    pygame.draw.rect(surface, config.CYAN, (bar_x + 40, y + 2, int((bar_w - 40) * xp_ratio), bar_h))
    pygame.draw.rect(surface, config.WHITE, (bar_x + 40, y + 2, bar_w - 40, bar_h), 1)
    y += 22

    surface.blit(font.render(f"Wave: {wave}   Kills: {kills}", True, config.WHITE), (8, y))
    y += 22
    surface.blit(font.render("Weapons:", True, config.GOLD), (8, y))
    y += 20
    for key, w in weapons.items():
        w_color = config.CYAN if w.get("type") == "target" else config.WHITE
        surface.blit(font_sm.render(f"  {w['name']} Lv{w['level']}", True, w_color), (8, y))
        y += 18

    if mode == "agent":
        right_lines = [
            (f"Episode: {episode}", config.WHITE),
            (f"Ep Reward: {episode_reward:.1f}", config.WHITE),
            (f"Epsilon:   {epsilon:.3f}", config.WHITE),
        ]
        for i, (text, color) in enumerate(right_lines):
            s = font.render(text, True, color)
            surface.blit(s, (sw - s.get_width() - 8, 8 + i * 22))

    if boss_alive:
        wf = pygame.font.SysFont(None, 36)
        bw = wf.render("!! BOSS ACTIVE !!", True, config.PURPLE)
        surface.blit(bw, (sw // 2 - bw.get_width() // 2, 8))


def draw_fast_button(surface, fast_mode):
    sw, sh = surface.get_size()
    font = pygame.font.SysFont(None, 24)
    label = ">> FAST  [F]" if not fast_mode else "|| SLOW  [F]"
    color = config.ORANGE if not fast_mode else config.DIM_GREEN
    bw, bh = 160, 36
    bx, by = sw - bw - 8, sh - bh - 8
    pygame.draw.rect(surface, color, (bx, by, bw, bh), border_radius=6)
    pygame.draw.rect(surface, config.WHITE, (bx, by, bw, bh), 2, border_radius=6)
    txt = font.render(label, True, config.BLACK)
    surface.blit(txt, (bx + (bw - txt.get_width()) // 2,
                        by + (bh - txt.get_height()) // 2))
    return pygame.Rect(bx, by, bw, bh)
