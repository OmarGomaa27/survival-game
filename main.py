import pygame
import sys
import game.config as config
from game.simulation import reset_episode, run_tick
from game.level_up import generate_level_up_choices, apply_choice
from game.stats import RunTracker
from rl.q_tabular import QLearningAgent, WeaponChoiceAgent
from rl.training import run_fast_training
from ui.rendering import (load_sprite, draw_map, draw_fog, draw_projectiles,
                          draw_hud, draw_fast_button)
from ui.effects import active_effects, draw_effects, update_effects
from ui.level_up_ui import run_level_up_ui
from ui.results_screen import show_results_screen


def run_mode_select(screen):
    sw, sh = screen.get_size()
    ft = pygame.font.SysFont(None, 48)
    fm = pygame.font.SysFont(None, 30)
    fs = pygame.font.SysFont(None, 22)
    while True:
        screen.fill((10, 10, 20))
        title = ft.render("Vampire Survivors RL", True, config.GOLD)
        screen.blit(title, (sw // 2 - title.get_width() // 2, sh // 4))
        sub = fm.render("Select Mode:", True, config.WHITE)
        screen.blit(sub, (sw // 2 - sub.get_width() // 2, sh // 4 + 60))
        agent_rect = pygame.Rect(sw // 2 - 160, sh // 2, 140, 50)
        pygame.draw.rect(screen, (20, 80, 20), agent_rect, border_radius=8)
        pygame.draw.rect(screen, config.GREEN, agent_rect, 2, border_radius=8)
        a_label = fm.render("[1] Agent", True, config.GREEN)
        screen.blit(a_label, (agent_rect.centerx - a_label.get_width() // 2,
                               agent_rect.centery - a_label.get_height() // 2))
        manual_rect = pygame.Rect(sw // 2 + 20, sh // 2, 140, 50)
        pygame.draw.rect(screen, (20, 20, 80), manual_rect, border_radius=8)
        pygame.draw.rect(screen, config.CYAN, manual_rect, 2, border_radius=8)
        m_label = fm.render("[2] Manual", True, config.CYAN)
        screen.blit(m_label, (manual_rect.centerx - m_label.get_width() // 2,
                               manual_rect.centery - m_label.get_height() // 2))
        hint1 = fs.render("Agent: Q-learning controls the game. Press F for fast training.", True, config.GREY)
        hint2 = fs.render("Manual: You play with arrow keys.", True, config.GREY)
        screen.blit(hint1, (sw // 2 - hint1.get_width() // 2, sh // 2 + 70))
        screen.blit(hint2, (sw // 2 - hint2.get_width() // 2, sh // 2 + 94))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: return "agent"
                if event.key == pygame.K_2: return "manual"
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if agent_rect.collidepoint(event.pos): return "agent"
                if manual_rect.collidepoint(event.pos): return "manual"


def main():
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Vampire Survivors RL -- Capstone")
    clock     = pygame.time.Clock()
    tile_font = pygame.font.SysFont(None, 22)
    mode = run_mode_select(screen)
    game_surface = pygame.Surface((config.W, config.H))
    spr_player = load_sprite("player.png")
    spr_enemy  = load_sprite("enemy.png")
    spr_boss   = load_sprite("boss.png")
    spr_gem    = load_sprite("gem.png")

    ACTIONS = [(0,-1),(0,1),(-1,0),(1,0),(0,0)]
    rl        = QLearningAgent(actions=ACTIONS, game_map=config.MAP)
    weapon_rl = WeaponChoiceAgent()
    episode, episode_reward = 0, 0.0
    reward_history = []
    last_tracker = None
    tracker  = RunTracker()
    ep_stats = tracker.start_episode()
    (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
     tick_count, agent_move_timer, active_projectiles, seen_tiles) = reset_episode()
    orbit_positions, boss_alive = [], False
    training_done, running = False, True
    player_action = (0, 0)
    rl_state  = rl.get_state(agent, enemies, gems)
    rl_action = rl.choose_action(rl_state)
    rl_accum  = 0.0

    while running:
        clock.tick(config.FPS)
        btn_rect = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.VIDEORESIZE:
                config.SCREEN_W = max(event.w, config.W + 40)
                config.SCREEN_H = max(event.h, config.H + 40)
                screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_f and mode == "agent":
                    config.FAST_MODE = True
                    episode, last_tracker = run_fast_training(rl, weapon_rl, reward_history, episode)
                    config.FAST_MODE = False
                    training_done = True
                if mode == "manual":
                    if event.key == pygame.K_UP:    player_action = (0,-1)
                    if event.key == pygame.K_DOWN:  player_action = (0,1)
                    if event.key == pygame.K_LEFT:  player_action = (-1,0)
                    if event.key == pygame.K_RIGHT: player_action = (1,0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect and btn_rect.collidepoint(event.pos) and mode == "agent":
                    config.FAST_MODE = True
                    episode, last_tracker = run_fast_training(rl, weapon_rl, reward_history, episode)
                    config.FAST_MODE = False
                    training_done = True

        if training_done:
            show_results_screen(screen, reward_history, last_tracker)
            training_done = False; running = False; continue

        episode_done = level_up = boss_win = False

        if mode == "agent":
            (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
             tick_count, agent_move_timer, active_projectiles, seen_tiles,
             reward, episode_done, orbit_positions, boss_alive,
             level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems, wave, kills, xp, xp_level,
                tick_count, agent_move_timer, active_projectiles, rl_action,
                seen_tiles, ep_stats=ep_stats)
            rl_accum += reward; episode_reward += reward
            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    w_states = weapon_rl.get_state(agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_states, len(choices))
                    weapon_rl.record_choice(w_states, idx)
                    q_weights = [weapon_rl.get_q(s) for s in w_states]
                    if ep_stats: ep_stats.weapon_choices.append((choices, q_weights, idx))
                    apply_choice(choices[idx], weapons)
            ep_stats.ticks = tick_count
            ep_stats.player_level = xp_level
            ep_stats.record_weapon_state(weapons)
            moved = (agent_move_timer == 0)
            if moved or episode_done:
                next_state = rl.get_state(agent, enemies, gems)
                rl.update(rl_state, rl_action, rl_accum, next_state)
                rl_accum = 0.0; rl_state = next_state
                rl_action = rl.choose_action(rl_state)
        else:
            (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
             tick_count, agent_move_timer, active_projectiles, seen_tiles,
             reward, episode_done, orbit_positions, boss_alive,
             level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems, wave, kills, xp, xp_level,
                tick_count, agent_move_timer, active_projectiles, player_action,
                seen_tiles)
            player_action = (0, 0)
            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    idx = run_level_up_ui(screen, choices, weapons)
                    apply_choice(choices[idx], weapons)

        if episode_done and mode == "manual":
            result_font = pygame.font.SysFont(None, 48)
            sub_font = pygame.font.SysFont(None, 28)
            overlay = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,180))
            screen.blit(overlay, (0,0))
            msg = (result_font.render("VICTORY -- Boss Defeated!", True, config.GOLD) if boss_win
                   else result_font.render("GAME OVER", True, config.RED))
            screen.blit(msg, (config.SCREEN_W//2 - msg.get_width()//2, config.SCREEN_H//3))
            for i, line in enumerate([f"Wave: {wave}  Kills: {kills}",
                                      f"Gems: {xp}  Level: {xp_level}",
                                      f"Survived: {tick_count/config.FPS:.1f}s"]):
                s = sub_font.render(line, True, config.WHITE)
                screen.blit(s, (config.SCREEN_W//2-s.get_width()//2, config.SCREEN_H//3+60+i*30))
            hint = sub_font.render("Press R to restart or ESC to quit", True, config.GREY)
            screen.blit(hint, (config.SCREEN_W//2-hint.get_width()//2, config.SCREEN_H//3+170))
            pygame.display.flip()
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                        if event.key == pygame.K_r:
                            (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
                             tick_count, agent_move_timer, active_projectiles, seen_tiles) = reset_episode()
                            boss_alive = False; active_effects.clear(); player_action = (0,0); waiting = False

        if episode_done and mode == "agent":
            import json
            reward_history.append(episode_reward); episode += 1
            won = boss_win or (tick_count >= config.MAX_TICKS)
            if boss_win and ep_stats: ep_stats.boss_win = True
            weapon_rl.update(episode_reward)
            tracker.end_episode(won=won); last_tracker = tracker; episode_reward = 0.0
            if episode >= config.MAX_EPISODES:
                with open("reward_history.json","w") as f: json.dump(reward_history, f)
                with open("run_stats.json","w") as f: json.dump(tracker.summary_dict(), f, indent=2)
                training_done = True
            (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
             tick_count, agent_move_timer, active_projectiles, seen_tiles) = reset_episode()
            boss_alive = False; ep_stats = tracker.start_episode(); active_effects.clear()
            rl_state = rl.get_state(agent, enemies, gems)
            rl_action = rl.choose_action(rl_state); rl_accum = 0.0
            if episode % 50 == 0:
                avg = sum(reward_history[-50:]) / 50
                print(f"Ep {episode:4d} | Avg(50): {avg:7.2f} | eps:{rl.epsilon:.3f}")

        # -- Draw --
        game_surface.fill(config.BLACK)
        draw_map(game_surface)
        for gx, gy in gems:
            if spr_gem: game_surface.blit(spr_gem, (gx*config.TILE, gy*config.TILE))
            else:
                rect = pygame.Rect(gx*config.TILE, gy*config.TILE, config.TILE, config.TILE)
                pygame.draw.rect(game_surface, config.YELLOW, rect)
                game_surface.blit(tile_font.render("*", True, config.BLACK), (gx*config.TILE+7, gy*config.TILE+4))
        for ox, oy in orbit_t < config.COLS and 0 <= sy < config.ROWS:
                pygame.draw.rect(game_surface, config.CYAN,
                                 pygame.Rect(sx*config.TILE, sy*config.TILE, config.TILE, config.TILE), 3)
        for e in enemies:
            if e.alive:
                if e.symbol == "B" and spr_boss: game_surface.blit(spr_boss, (e.x*config.TILE, e.y*config.TILE))
                elif e.symbol != "B" and spr_enemy: game_surface.blit(spr_enemy, (e.x*config.TILE, e.y*config.TILE))
                else: e.draw(game_surface, config.TILE, tile_font)
        if spr_player: game_surface.blit(spr_player, (agent.x*config.TILE, agent.y*config.TILE))
        else: agent.draw(game_surface, tile_font)
        draw_fog(game_surface, agent)
        screen.fill(config.BLACK)
        screen.blit(game_surface, ((config.SCREEN_W-config.W)//2, (config.SCREEN_H-config.H)//2))
        draw_hud(screen, agent, wave, kills, xp, xp_level, weapons,
                 episode, episode_reward, rl.epsilon, config.FAST_MODE, boss_alive, mode)
        btn_rect = draw_fast_button(screen, config.FAST_MODE) if mode == "agent" else None
        pygame.display.flip()

    pygame.quit(); sys.exit()


if __name__ == "__main__":
    main()
