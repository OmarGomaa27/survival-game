"""
Run after training to diagnose agent behavior.
Usage: python diagnosis.py

Trains 5000 episodes headless, then prints:
1. Movement policy (what the agent does in key situations)
2. Q-table coverage (how many states visited)
3. Weapon agent preferences
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from game.config import MAP, MAX_TICKS
from game.simulation import reset_episode, run_tick
from game.level_up import generate_level_up_choices, apply_choice
from game.stats import RunTracker
from rl.q_tabular import QLearningAgent, WeaponChoiceAgent

ACTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)]
EPISODES = 5000


def train(rl, weapon_rl):
    tracker = RunTracker()
    for ep in range(EPISODES):
        (agent, weapons, enemies, gems, wave, kills, xp, xp_level,
         tick_count, agent_move_timer, active_projectiles, seen_tiles) = reset_episode()
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
                    w_states = weapon_rl.get_state(agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_states, len(choices))
                    weapon_rl.record_choice(w_states, idx)
                    apply_choice(choices[idx], weapons)

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

        if (ep + 1) % 1000 == 0:
            wr = tracker.win_rate() * 100
            print(f"  Training... {ep+1}/{EPISODES}  WR: {wr:.1f}%")

    return tracker


def diagnose_movement(rl):
    labels = {(0,-1): "UP", (0,1): "DOWN", (-1,0): "LEFT",
              (1,0): "RIGHT", (0,0): "STAY"}

    print("\n" + "=" * 60)
    print("MOVEMENT POLICY DIAGNOSIS")
    print("=" * 60)

    for hp_b, hp_label in [(0, "CRITICAL HP (<=25)"), (1, "LOW HP (<=50)"), (2, "OK HP (>50)")]:
        print(f"\n{'─' * 50}")
        print(f"  {hp_label}")
        print(f"{'─' * 50}")

        for enemy_dist, ed_label in [(0, "ADJACENT"), (1, "CLOSE"), (2, "MEDIUM"), (3, "NONE")]:
            for gem_dist, gd_label in [(0, "NEAR"), (1, "MID"), (2, "FAR")]:
                actions_seen = {}
                for ex, ey in [(-1,0), (1,0), (0,-1), (0,1), (0,0)]:
                    for gx, gy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        for wall in [0, 1, 2, 3]:
                            state = (ex, ey, enemy_dist, gx, gy, gem_dist, wall, hp_b)
                            qs = {a: rl.get_q(state, a) for a in ACTIONS}
                            best = max(qs, key=qs.get)
                            if qs[best] != 0:
                                name = labels[best]
                                actions_seen[name] = actions_seen.get(name, 0) + 1

                if actions_seen:
                    total = sum(actions_seen.values())
                    summary = ", ".join(f"{k}: {v/total*100:.0f}%"
                                       for k, v in sorted(actions_seen.items(),
                                                          key=lambda x: -x[1]))
                    print(f"  Enemy {ed_label:8s} + Gem {gd_label:4s} -> {summary}")


def diagnose_qtable(rl):
    print("\n" + "=" * 60)
    print("Q-TABLE COVERAGE")
    print("=" * 60)

    total_states = len(rl.q_table)
    total_entries = sum(len(v) for v in rl.q_table.values())

    print(f"  States visited:      {total_states}")
    print(f"  State-action pairs:  {total_entries}")
    print(f"  Theoretical max:     ~3888 states x 5 actions = ~19440")
    print(f"  Coverage:            {total_states / 3888 * 100:.1f}% of states")

    # Q-value distribution
    all_q = []
    for s, actions in rl.q_table.items():
        for a, q in actions.items():
            all_q.append(q)

    if all_q:
        all_q.sort()
        print(f"\n  Q-value range:       [{min(all_q):.1f}, {max(all_q):.1f}]")
        print(f"  Q-value median:      {all_q[len(all_q)//2]:.1f}")
        print(f"  Q-values near zero:  {sum(1 for q in all_q if abs(q) < 1.0)} "
              f"({sum(1 for q in all_q if abs(q) < 1.0)/len(all_q)*100:.0f}%)")


def diagnose_flee_vs_chase(rl):
    """Check if the agent differentiates behavior by HP level."""
    labels = {(0,-1): "UP", (0,1): "DOWN", (-1,0): "LEFT",
              (1,0): "RIGHT", (0,0): "STAY"}

    print("\n" + "=" * 60)
    print("FLEE vs CHASE ANALYSIS")
    print("  Does the agent behave differently at low HP?")
    print("=" * 60)

    for enemy_dist, ed_label in [(0, "ADJACENT"), (1, "CLOSE")]:
        print(f"\n  Enemy {ed_label}, gem NEAR:")
        for hp_b, hp_label in [(2, "OK HP"), (1, "LOW HP"), (0, "CRITICAL")]:
            flee = chase = stay = 0
            for ex, ey in [(-1,0), (1,0), (0,-1), (0,1)]:
                for gx, gy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    state = (ex, ey, enemy_dist, gx, gy, 0, 0, hp_b)
                    qs = {a: rl.get_q(state, a) for a in ACTIONS}
                    best = max(qs, key=qs.get)
                    if qs[best] == 0:
                        continue
                    if ex != 0 and best[0] == -ex:
                        flee += 1
                    elif ey != 0 and best[1] == -ey:
                        flee += 1
                    elif gx != 0 and best[0] == gx:
                        chase += 1
                    elif gy != 0 and best[1] == gy:
                        chase += 1
                    elif best == (0, 0):
                        stay += 1

            total = flee + chase + stay
            if total > 0:
                print(f"    {hp_label:10s}: FLEE {flee/total*100:4.0f}% | "
                      f"CHASE gem {chase/total*100:4.0f}% | "
                      f"STAY {stay/total*100:4.0f}%")
            else:
                print(f"    {hp_label:10s}: (no data)")


def diagnose_weapons(weapon_rl):
    print("\n" + "=" * 60)
    print("WEAPON AGENT Q-VALUES")
    print("=" * 60)

    wnames = {0: "Wand", 1: "Axe", 2: "Whip", 3: "Books"}

    print(f"\n  States in Q-table: {len(weapon_rl.q_table)}")
    print(f"  Epsilon: {weapon_rl.epsilon:.3f}")

    # Average Q per weapon across all contexts
    weapon_q_sums = {}
    weapon_q_counts = {}
    for state, q_val in weapon_rl.q_table.items():
        # state = (hp_b, wave_b, pressure, is_new, weapon_id, level_bracket)
        wid = state[4]
        name = wnames.get(wid, f"id{wid}")
        weapon_q_sums[name] = weapon_q_sums.get(name, 0.0) + q_val
        weapon_q_counts[name] = weapon_q_counts.get(name, 0) + 1

    print("\n  Average Q-value by weapon (higher = agent thinks it's better):")
    for name in ["Wand", "Axe", "Whip", "Books"]:
        if name in weapon_q_counts:
            avg = weapon_q_sums[name] / weapon_q_counts[name]
            n = weapon_q_counts[name]
            print(f"    {name:12s}: avg Q = {avg:8.1f}  ({n} states)")
        else:
            print(f"    {name:12s}: (no data)")

    # New vs upgrade preference
    print("\n  New weapon vs upgrade preference:")
    new_q = []
    upgrade_q = []
    for state, q_val in weapon_rl.q_table.items():
        if state[3] == 1:  # is_new
            new_q.append(q_val)
        else:
            upgrade_q.append(q_val)
    if new_q:
        print(f"    New weapon:  avg Q = {sum(new_q)/len(new_q):.1f}  ({len(new_q)} entries)")
    if upgrade_q:
        print(f"    Upgrade:     avg Q = {sum(upgrade_q)/len(upgrade_q):.1f}  ({len(upgrade_q)} entries)")


def main():
    print(f"Training {EPISODES} episodes for diagnosis...\n")
    rl = QLearningAgent(actions=ACTIONS, game_map=MAP)
    weapon_rl = WeaponChoiceAgent()
    tracker = train(rl, weapon_rl)

    print(f"\n  Final: {tracker.episodes} eps, "
          f"WR: {tracker.win_rate()*100:.1f}%, "
          f"Avg survived: {tracker.avg_ticks():.0f} ticks")

    diagnose_movement(rl)
    diagnose_qtable(rl)
    diagnose_flee_vs_chase(rl)
    diagnose_weapons(weapon_rl)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()