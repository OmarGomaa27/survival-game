"""
Learning Rate Experiment
Tests multiple alpha values for both movement and weapon agents.
Usage: python lr_experiment.py
Takes ~18 minutes. Prints tables and saves to lr_results.csv
"""
import os, csv, time
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from game.config import MAP, MAX_TICKS
from game.simulation import reset_episode, run_tick
from game.level_up import generate_level_up_choices, apply_choice
from game.stats import RunTracker
from rl.q_tabular import QLearningAgent, WeaponChoiceAgent

ACTIONS = [(0,-1),(0,1),(-1,0),(1,0),(0,0)]
EPISODES_PER_RUN = 20000
TAIL = 1000  # avg over last N episodes for final metrics


def run_experiment(move_alpha, weapon_alpha, label=""):
    rl = QLearningAgent(actions=ACTIONS, game_map=MAP, alpha=move_alpha)
    weapon_rl = WeaponChoiceAgent(alpha=weapon_alpha)
    tracker = RunTracker()
    rewards = []

    for ep in range(EPISODES_PER_RUN):
        (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
         tick_count, agent_move_timer, active_projectiles,
         seen_tiles) = reset_episode()
        ep_stats = tracker.start_episode()
        state = rl.get_state(agent, enemies, gems)
        action = rl.choose_action(state)
        accum = ep_reward = 0.0

        while True:
            (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
             tick_count, agent_move_timer, active_projectiles, seen_tiles,
             reward, done, _, _, level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems, wave, kills, xp, xp_level,
                tick_count, agent_move_timer, active_projectiles, action,
                seen_tiles, ep_stats=ep_stats)

            accum += reward
            ep_reward += reward

            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    w_states = weapon_rl.get_state(
                        agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_states, len(choices))
                    weapon_rl.record_choice(w_states, idx)
                    apply_choice(choices[idx], weapons)
                ep_stats.record_weapon_state(weapons)

            ep_stats.ticks = tick_count
            ep_stats.player_level = xp_level

            moved = (agent_move_timer == 0)
            if moved or done:
                next_state = rl.get_state(agent, enemies, gems)
                rl.update(state, action, accum, next_state)
                accum = 0.0
                if done:
                    won = boss_win or (tick_count >= MAX_TICKS)
                    if boss_win:
                        ep_stats.boss_win = True
                    ep_stats.record_weapon_state(weapons)
                    weapon_rl.update(ep_reward)
                    tracker.end_episode(won=won)
                    break
                state = next_state
                action = rl.choose_action(state)

        rewards.append(ep_reward)

        if (ep + 1) % 5000 == 0:
            tail_avg = sum(rewards[-TAIL:]) / min(len(rewards), TAIL)
            print(f"    {label} ep {ep+1:5d} | "
                  f"Avg({TAIL}): {tail_avg:.1f} | "
                  f"WR: {tracker.win_rate()*100:.1f}%")

    # Final metrics from last TAIL episodes
    tail_rewards = rewards[-TAIL:]
    avg_reward = sum(tail_rewards) / len(tail_rewards)
    win_rate = tracker.win_rate() * 100
    avg_ticks = tracker.avg_ticks()
    avg_gems = tracker.avg_gems()
    avg_level = tracker.avg_player_level()

    # Stability: std dev of last TAIL rewards
    mean = avg_reward
    variance = sum((r - mean)**2 for r in tail_rewards) / len(tail_rewards)
    stability = variance ** 0.5

    return {
        "avg_reward": avg_reward,
        "win_rate": win_rate,
        "avg_ticks": avg_ticks,
        "avg_gems": avg_gems,
        "avg_level": avg_level,
        "stability": stability,
    }


def print_table(title, headers, rows):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    fmt = "  {:>8s}" * len(headers)
    print(fmt.format(*headers))
    print(f"  {'-'*8*len(headers)}")
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))


def main():
    all_results = []
    start = time.time()

    # ── Movement agent alpha experiments ──────────────────────
    # Bracket current α=0.3: two below, current, two above
    move_alphas = [0.05, 0.1, 0.3, 0.5, 0.7]
    weapon_alpha_fixed = 0.15
    move_results = []

    print("\n" + "="*60)
    print("MOVEMENT AGENT LEARNING RATE EXPERIMENT")
    print(f"  Weapon alpha fixed at {weapon_alpha_fixed}")
    print(f"  {EPISODES_PER_RUN} episodes per run")
    print("="*60)

    for alpha in move_alphas:
        label = f"move_a={alpha}"
        print(f"\n  Running {label} ...")
        r = run_experiment(alpha, weapon_alpha_fixed, label)
        move_results.append(r)
        all_results.append({
            "agent": "movement", "alpha": alpha,
            **r
        })
        print(f"  Done: avg_reward={r['avg_reward']:.1f}  "
              f"WR={r['win_rate']:.1f}%  "
              f"stability={r['stability']:.1f}")

    # ── Weapon agent alpha experiments ────────────────────────
    # Bracket current α=0.15: two below, current, two above
    weapon_alphas = [0.01, 0.05, 0.15, 0.3, 0.5]
    move_alpha_fixed = 0.3
    weapon_results = []

    print("\n" + "="*60)
    print("WEAPON AGENT LEARNING RATE EXPERIMENT")
    print(f"  Movement alpha fixed at {move_alpha_fixed}")
    print(f"  {EPISODES_PER_RUN} episodes per run")
    print("="*60)

    for alpha in weapon_alphas:
        label = f"weap_a={alpha}"
        print(f"\n  Running {label} ...")
        r = run_experiment(move_alpha_fixed, alpha, label)
        weapon_results.append(r)
        all_results.append({
            "agent": "weapon", "alpha": alpha,
            **r
        })
        print(f"  Done: avg_reward={r['avg_reward']:.1f}  "
              f"WR={r['win_rate']:.1f}%  "
              f"stability={r['stability']:.1f}")

    elapsed = time.time() - start
    print(f"\n\nTotal time: {elapsed/60:.1f} minutes")

    # ── Print tables ──────────────────────────────────────────
    headers = ["Alpha", "Avg Rwd", "Win%", "Avg Ticks",
               "Avg Gems", "Avg Lvl", "Std Dev"]

    rows = []
    for alpha, r in zip(move_alphas, move_results):
        rows.append([
            f"{alpha}", f"{r['avg_reward']:.1f}", f"{r['win_rate']:.1f}%",
            f"{r['avg_ticks']:.0f}", f"{r['avg_gems']:.1f}",
            f"{r['avg_level']:.1f}", f"{r['stability']:.0f}"
        ])
    print_table("MOVEMENT AGENT — Learning Rate Comparison "
                f"(weapon α={weapon_alpha_fixed})", headers, rows)

    rows = []
    for alpha, r in zip(weapon_alphas, weapon_results):
        rows.append([
            f"{alpha}", f"{r['avg_reward']:.1f}", f"{r['win_rate']:.1f}%",
            f"{r['avg_ticks']:.0f}", f"{r['avg_gems']:.1f}",
            f"{r['avg_level']:.1f}", f"{r['stability']:.0f}"
        ])
    print_table("WEAPON AGENT — Learning Rate Comparison "
                f"(movement α={move_alpha_fixed})", headers, rows)

    # ── Best results ──────────────────────────────────────────
    best_move = max(zip(move_alphas, move_results),
                    key=lambda x: x[1]["win_rate"])
    best_weap = max(zip(weapon_alphas, weapon_results),
                    key=lambda x: x[1]["win_rate"])
    print(f"\n  Best movement α: {best_move[0]} "
          f"(WR={best_move[1]['win_rate']:.1f}%)")
    print(f"  Best weapon α:   {best_weap[0]} "
          f"(WR={best_weap[1]['win_rate']:.1f}%)")

    # ── Save CSV ──────────────────────────────────────────────
    fname = "lr_results.csv"
    with open(fname, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "agent", "alpha", "avg_reward", "win_rate",
            "avg_ticks", "avg_gems", "avg_level", "stability"])
        w.writeheader()
        for row in all_results:
            w.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v)
                        for k, v in row.items()})
    print(f"\n  Saved results to {fname}")
    print("  Done!")


if __name__ == "__main__":
    main()