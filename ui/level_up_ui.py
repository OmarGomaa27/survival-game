import pygame
import sys
from game.config import GOLD, WHITE, GREEN, CYAN, YELLOW, GREY, ORANGE
from game.weapons import WEAPON_POOL, WEAPON_SCALING


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
    gap = 20
    start_x = sw // 2 - (3 * card_w + 2 * gap) // 2
    card_y  = sh // 2 - card_h // 2
    rects = []
    for i, (kind, key) in enumerate(choices):
        cx = start_x + i * (card_w + gap)
        rect = pygame.Rect(cx, card_y, card_w, card_h)
        rects.append(rect)
        bg = (15, 55, 15) if kind == "new" else (40, 15, 60)
        pygame.draw.rect(surface, bg, rect, border_radius=8)
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
            s1 = fh.render(f"Block: {int(scale['block_chance']*100)}%", True, YELLOW)
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
