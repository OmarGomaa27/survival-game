import json
import game.config as config
from game.config import MAX_EPISODES, MAX_TICKS, TOTAL_WALKABLE
from game.simulation import reset_episode, run_tick
from game.level_up import generate_level_up_choices, apply_choice
from game.stats import RunTracker


def run_fast_training(rl, weapon_rl, reward_history, start_episode):
    tracker = RunTracker()
    episode = start_episode
    print(f"\n[FAST] Starting training from episode {episode} ...")

    while episode < MAX_EPISODES:
        (agent, weapons, enemies, gems,
         wave, kills, xp, xp_level,
         tick_count, agent_move_timer,
         active_projectiles, seen_tiles) = reset_episode()
        episode_reward = 0.0
        ep_stats = tracker.start_episode()

        state  = rl.get_state(agent, enemies, gems)
        action = rl.choose_action(state)
        accum_reward = 0.0

        while True:
            (agent, weapons, enemies, gems,
             wave, kills, xp, xp_level,
             tick_count, agent_move_timer,
             active_projectiles, seen_tiles, reward,
             done, _, _, level_up, boss_win) = run_tick(
                agent, weapons, enemies, gems,
                wave, kills, xp, xp_level,
                tick_count, agent_move_timer,
                active_projectiles, action,
                seen_tiles, ep_stats=ep_stats)

            accum_reward   += reward
            episode_reward += reward

            if level_up:
                choices = generate_level_up_choices(weapons)
                if choices:
                    w_states = weapon_rl.get_state(agent, enemies, weapons, wave, choices)
                    idx = weapon_rl.choose(w_states, len(choices))
                    weapon_rl.record_choice(w_states, idx)
                    q_weights = [weapon_rl.get_q(s) for s in w_states]
                    if ep_stats:
                        ep_stats.weapon_choices.append((choices, q_weights, idx))
                    apply_choice(choices[idx], weapons)
                ep_stats.record_weapon_state(weapons)

            ep_stats.ticks        = tick_count
            ep_stats.player_level = xp_level

            moved = (agent_move_timer == 0)
            if moved or done:
                next_state = rl.get_state(agent, enemies, gems)
                rl.update(state, action, accum_reward, next_state)
                accum_reward = 0.0
                if done:
                    won = boss_win or (tick_count >= MAX_TICKS)
                    if boss_win:
                        ep_stats.boss_win = True
                    ep_stats.record_weapon_state(weapons)
                    weapon_rl.update(episode_reward)
                    tracker.end_episode(won=won)
                    break
                state  = next_state
                action = rl.choose_action(state)

        reward_history.append(episode_reward)
        episode += 1

        if episode % 100 == 0:
            avg = sum(reward_history[-100:]) / 100
            wr  = tracker.win_rate() * 100
            print(f"  Ep {episode:5d} | Avg(100): {avg:8.2f} | "
                  f"WinRate: {wr:.1f}% | eps:{rl.epsilon:.3f}")

        if episode % 1000 == 0 and episode > 0:
            print(f"\n  --- Diagnostics at ep {episode} ---")
            print(f"    Avg Ticks:  {tracker.avg_ticks():.0f}")
            print(f"    Avg Gems:   {tracker.avg_gems():.1f}")
            print(f"    Gem-> ratio: {tracker.gem_approach_ratio()*100:.0f}%")
            print(f"    Map seen:   {tracker.avg_tiles_revealed()/TOTAL_WALKABLE*100:.0f}%")
            print(f"    Boss wins:  {tracker.boss_win_count()}")
            cs = tracker.choice_summary()
            if cs:
                print("    Weapon choices:")
                for e in cs:
                    pct = (e["picked_total"] / max(e["offered"], 1)) * 100
                    print(f"      {e['key']:10s}  offered:{e['offered']:5d}  "
                          f"picked:{e['picked_total']:4d} ({pct:4.1f}%)")
            print()

    print(f"\n[DONE] {episode} episodes completed | Wins: {tracker.wins}")
    with open("reward_history.json", "w") as f:
        json.dump(reward_history, f)
    with open("run_stats.json", "w") as f:
        json.dump(tracker.summary_dict(), f, indent=2)
    print("   Saved reward_history.json + run_stats.json")
    return episode, tracker
