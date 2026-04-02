import pygame
import game.config as config


def render_results_surface(reward_history, sw, tracker=None):
    """Render the full training results to an off-screen surface."""
    content_h = 1200
    if tracker:
        hist = tracker.gems_at_death_histogram()
        content_h += min(len(hist), 12) * 16
        content_h += len(tracker.choice_summary()) * 18 + 80
    surf = pygame.Surface((sw, content_h))
    surf.fill((10, 10, 20))

    fb  = pygame.font.SysFont(None, 44)
    fm  = pygame.font.SysFont(None, 28)
    fs  = pygame.font.SysFont(None, 22)
    fxs = pygame.font.SysFont(None, 19)

    title = fb.render("TRAINING COMPLETE", True, config.YELLOW)
    surf.blit(title, (sw // 2 - title.get_width() // 2, 10))

    total   = len(reward_history)
    avg_all = sum(reward_history) / max(total, 1)
    first50 = sum(reward_history[:50]) / 50 if total >= 50 else 0
    last50  = sum(reward_history[-50:]) / 50 if total >= 50 else 0
    best    = max(reward_history)
    worst   = min(reward_history)

    left = [
        (f"Episodes:       {total}",             config.WHITE),
        (f"Avg (all):      {avg_all:.1f}",       config.WHITE),
        (f"Avg (first 50): {first50:.1f}",       config.WHITE),
        (f"Avg (last 50):  {last50:.1f}",        config.WHITE),
        (f"Best:           {best:.1f}",          config.GOLD),
        (f"Worst:          {worst:.1f}",         config.WHITE),
        (f"Improvement:    {last50-first50:+.1f}",
         config.GREEN if last50 > first50 else config.RED),
    ]
    for i, (text, color) in enumerate(left):
        surf.blit(fm.render(text, True, color), (12, 52 + i * 26))

    if tracker:
        right = [
            (f"Win Rate:       {tracker.win_rate()*100:.1f}%",
             config.GREEN if tracker.win_rate() > 0.1 else config.WHITE),
            (f"Total Wins:     {tracker.wins}",              config.WHITE),
            (f"Boss Kills:     {tracker.boss_kills_total}",  config.PURPLE),
            (f"Max Plyr Level: {tracker.max_player_level}",  config.CYAN),
            (f"Avg Plyr Level: {tracker.avg_player_level():.1f}", config.CYAN),
        ]
        for i, (text, color) in enumerate(right):
            s = fm.render(text, True, color)
            surf.blit(s, (sw - s.get_width() - 12, 52 + i * 26))

    dy = 52 + 7 * 26 + 8
    if tracker:
        pygame.draw.line(surf, config.GREY, (8, dy - 4), (sw - 8, dy - 4), 1)
        surf.blit(fs.render("DIAGNOSTICS", True, config.GOLD), (8, dy))
        dy += 22
        approach_pct   = tracker.gem_approach_ratio() * 100
        approach_color = config.GREEN if approach_pct > 60 else (config.YELLOW if approach_pct > 50 else config.RED)
        pct5        = tracker.pct_reaching_n_gems(5) * 100
        explore_pct = tracker.avg_tiles_revealed() / max(config.TOTAL_WALKABLE, 1) * 100
        FPS = config.FPS
        diag_left = [
            (f"Avg Survived:       {tracker.avg_ticks()/FPS:.1f}s ({tracker.avg_ticks():.0f} ticks)", config.WHITE),
            (f"Avg Gems Collected: {tracker.avg_gems():.1f}", config.WHITE),
            (f"Reach 5 Gems:       {pct5:.1f}%", config.GREEN if pct5 > 10 else config.WHITE),
            (f"Avg Map Explored:   {explore_pct:.0f}%", config.GREEN if explore_pct > 30 else config.WHITE),
        ]
        diag_right = [
            (f"Avg Hits Taken:  {tracker.avg_hits_taken():.1f}", config.WHITE),
            (f"Avg Dmg Taken:   {tracker.avg_damage_taken():.0f}", config.WHITE),
            (f"Gem Approach %:  {approach_pct:.0f}%", approach_color),
        ]
        for i, (text, color) in enumerate(diag_left):
            surf.blit(fs.render(text, True, color), (12, dy + i * 20))
        for i, (text, color) in enumerate(diag_right):
            s = fs.render(text, True, color)
            surf.blit(s, (sw - s.get_width() - 12, dy + i * 20))
        dy += max(len(diag_left), len(diag_right)) * 20 + 4

        hist = tracker.gems_at_death_histogram()
        if hist:
            surf.blit(fs.render("Gems Collected Per Episode:", True, config.GOLD), (12, dy))
            dy += 18
            max_count = max(c for _, c in hist)
            bar_area = sw - 24
            for g_count, count in hist[:12]:
                pct     = count / max(total, 1) * 100
                pct_bar = count / max_count
                bar_w   = max(int(pct_bar * (bar_area - 180)), 1)
                label   = fxs.render(f"{g_count:2d} gems:", True, config.CYAN)
                surf.blit(label, (12, dy))
                pygame.draw.rect(surf, config.CYAN, (70, dy + 2, bar_w, 12))
                ct = fxs.render(f"{count} ({pct:.1f}%)", True, config.GREY)
                surf.blit(ct, (74 + bar_w, dy))
                dy += 16
            dy += 4
        pygame.draw.line(surf, config.GREY, (8, dy), (sw - 8, dy), 1)
        dy += 4

    if tracker:
        WNAMES = {"wand":"Magic Wand","axe":"Axe","whip":"Whip","books":"Spell Books","shield":"Shield"}
        keys = tracker.all_weapon_keys()
        ty = dy
        pygame.draw.line(surf, config.GREY, (8, ty - 4), (sw - 8, ty - 4), 1)
        headers = ["Weapon","Apps","DPS","Max DPS","Win%","Avg Lv"]
        n_cols = len(headers)
        col_pad = 12
        col_span = (sw - 2*col_pad) / n_cols
        col_x = [int(col_pad + i*col_span) for i in range(n_cols)]
        for cx, h in zip(col_x, headers):
            surf.blit(fs.render(h, True, config.GOLD), (cx, ty))
        pygame.draw.line(surf, config.GREY, (8, ty+18), (sw-8, ty+18), 1)
        for row, key in enumerate(keys):
            ry = ty + 24 + row * 22
            name = WNAMES.get(key, key)
            vals = [name, str(tracker.weapon_appearances(key)),
                    f"{tracker.weapon_avg_dps(key):.2f}", f"{tracker.weapon_max_dps(key):.2f}",
                    f"{tracker.weapon_win_rate(key)*100:.1f}%", f"{tracker.weapon_avg_level(key):.1f}"]
            rc = config.CYAN if row % 2 == 0 else config.WHITE
            for cx, v in zip(col_x, vals):
                surf.blit(fxs.render(v, True, rc), (cx, ry))
        dy = ty + 24 + len(keys) * 22 + 6
        pygame.draw.line(surf, config.GREY, (8, dy), (sw - 8, dy), 1)

    if tracker and tracker.total_levelups() > 0:
        dy += 6
        surf.blit(fs.render(f"WEAPON CHOICES  ({tracker.total_levelups()} level-ups)", True, config.GOLD), (8, dy))
        dy += 22
        ch_h = ["Weapon","Offered","Picked","New","Upgr","Pick%","Avg Wt"]
        n_ch = len(ch_h)
        ch_pad = 12
        ch_span = (sw - 2*ch_pad) / n_ch
        ch_x = [int(ch_pad + i*ch_span) for i in range(n_ch)]
        for cx, h in zip(ch_x, ch_h):
            surf.blit(fxs.render(h, True, config.GOLD), (cx, dy))
        dy += 18
        pygame.draw.line(surf, config.GREY, (8, dy-2), (sw-8, dy-2), 1)
        WNAMES2 = {"wand":"Magic Wand","axe":"Axe","whip":"Whip","books":"Spell Books","shield":"Shield"}
        for i, entry in enumerate(tracker.choice_summary()):
            name = WNAMES2.get(entry["key"], entry["key"])
            pp = (entry["picked_total"] / max(entry["offered"], 1)) * 100
            vals = [name, str(entry["offered"]), str(entry["picked_total"]),
                    str(entry["picked_new"]), str(entry["picked_upgrade"]),
                    f"{pp:.1f}%", f"{entry['avg_weight']:.3f}"]
            rc = config.CYAN if i % 2 == 0 else config.WHITE
            for cx, v in zip(ch_x, vals):
                surf.blit(fxs.render(v, True, rc), (cx, dy))
            dy += 18
        dy += 4
        pygame.draw.line(surf, config.GREY, (8, dy), (sw - 8, dy), 1)

    dy += 8
    cx, cy = 10, dy
    cw, ch = sw - 20, 200
    if total > 1:
        pygame.draw.rect(surf, config.DARK_GREY, (cx, cy, cw, ch))
        pygame.draw.rect(surf, config.GREY, (cx, cy, cw, ch), 1)
        mn, mx = min(reward_history), max(reward_history)
        rng = mx - mn if mx != mn else 1
        window = max(10, total // 100)
        smoothed, running = [], 0.0
        for i, r in enumerate(reward_history):
            running += r
            if i >= window: running -= reward_history[i - window]
            smoothed.append(running / min(i + 1, window))
        raw_pts = [(cx + int(i/(total-1)*cw), cy + ch - int((r-mn)/rng*ch))
                   for i, r in enumerate(reward_history)]
        if len(raw_pts) > 1:
            pygame.draw.lines(surf, (40,100,100), False, raw_pts, 1)
        sm_pts = [(cx + int(i/(total-1)*cw), cy + ch - int((r-mn)/rng*ch))
                  for i, r in enumerate(smoothed)]
        if len(sm_pts) > 1:
            pygame.draw.lines(surf, config.CYAN, False, sm_pts, 2)
        surf.blit(fxs.render("Ep 1", True, config.GREY), (cx+2, cy+ch-14))
        lr = fxs.render(f"Ep {total}", True, config.GREY)
        surf.blit(lr, (cx+cw-lr.get_width()-2, cy+ch-14))
        surf.blit(fxs.render("Reward per Episode (smoothed)", True, config.GOLD), (cx+4, cy+4))
        surf.blit(fxs.render(f"{mx:.0f}", True, config.GREY), (cx+2, cy+16))
        surf.blit(fxs.render(f"{mn:.0f}", True, config.GREY), (cx+2, cy+ch-28))
    dy = cy + ch + 8
    hint = fs.render("[ESC] Quit    [P] Export PNG    [D] Export CSV", True, config.WHITE)
    surf.blit(hint, (sw // 2 - hint.get_width() // 2, dy))
    dy += 24
    final = pygame.Surface((sw, dy))
    final.blit(surf, (0, 0))
    return final


def show_results_screen(screen, reward_history, tracker=None):
    results_surf = render_results_surface(reward_history, config.SCREEN_W, tracker)
    scroll_y = 0
    max_scroll = max(0, results_surf.get_height() - config.SCREEN_H)
    needs_rerender = False

    def export_png():
        fname = "results_screen.png"
        pygame.image.save(results_surf, fname)
        print(f"[EXPORT] Saved screenshot to {fname}")

    def export_csv():
        if not tracker: return
        import csv
        fname = "training_results.csv"
        with open(fname, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric","Value"])
            w.writerow(["Episodes", tracker.episodes])
            w.writerow(["Wins", tracker.wins])
            w.writerow(["Win Rate", f"{tracker.win_rate()*100:.1f}%"])
            w.writerow(["Boss Kills", tracker.boss_kills_total])
            for key in tracker.all_weapon_keys():
                w.writerow([key, tracker.weapon_appearances(key)])
            w.writerow([])
            w.writerow(["Episode","Reward"])
            for i, r in enumerate(reward_history):
                w.writerow([i+1, f"{r:.1f}"])
        print(f"[EXPORT] Saved {fname}")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            elif event.type == pygame.VIDEORESIZE:
                config.SCREEN_W = max(event.w, 600)
                config.SCREEN_H = max(event.h, 400)
                screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), pygame.RESIZABLE)
                needs_rerender = True
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(scroll_y - event.y * 30, max_scroll))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:    scroll_y = max(0, scroll_y - 30)
                elif event.key == pygame.K_DOWN: scroll_y = min(max_scroll, scroll_y + 30)
                elif event.key == pygame.K_p:   export_png()
                elif event.key == pygame.K_d:   export_csv()
        if needs_rerender:
            results_surf = render_results_surface(reward_history, config.SCREEN_W, tracker)
            max_scroll = max(0, results_surf.get_height() - config.SCREEN_H)
            scroll_y = min(scroll_y, max_scroll)
            needs_rerender = False
        screen.fill((10, 10, 20))
        screen.blit(results_surf, (0, -scroll_y))
        if max_scroll > 0:
            sh = config.SCREEN_H
            bar_h = max(20, int(sh * sh / results_surf.get_height()))
            bar_y = int(scroll_y / max_scroll * (sh - bar_h))
            pygame.draw.rect(screen, config.GREY, (config.SCREEN_W - 8, bar_y, 6, bar_h), border_radius=3)
        pygame.display.flip()
