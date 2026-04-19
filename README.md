# Survivor Game RL Project

A roguelike survival game where a tabular Q-learning agent learns to navigate, collect gems, select weapons, and survive waves of enemies.

---

## Overview

This project implements and evaluates tabular Q-learning (Watkins & Dayan, 1992) in a custom game environment that goes beyond standard gridworld benchmarks. The agent faces:

- **Partial observability**: fog of war limits vision to a 3 tile radius
- **Compound decision-making**: one Q-agent controls movement, a second controls weapon selection
- **Dynamic difficulty**: enemy waves escalate over time, with a boss spawning at the 6-minute mark
- **Strategic weapon diversity**: 4 weapons with distinct mechanics including lifesteal

The core research question: *Can tabular Q-learning learn meaningful behavior in an environment with fog of war, compound decisions, and dynamic difficulty, using only reward shaping and state representation design?*

---

## Quick Start

### Requirements

- Python 3.10+
- pip

### Setup

```bash
git clone https://github.com/omargomaa27/survival-game.git
```

```bash
cd survival-game
```

```bash
python -m venv .venv
```

```bash
# Windows
.venv\Scripts\activate
```

```bash
# macOS/Linux
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

- Press **1** for Agent mode (Q-learning controls the game)
- Press **2** for Manual mode (you play with arrow keys)
- In Agent mode, press **F** to start headless fast training

---

## Game Mechanics

| Mechanic | Details |
|----------|---------
| Map | 20×20 tile grid with internal walls |
| Fog of War | Agent sees 3-tile radius only |
| Enemies | Chase player, spawn in escalating waves |
| Boss | Spawns at tick 2880 (6 min), 300 HP, 25 damage |
| Gems | Dropped by killed enemies, 5 gems = 1 level-up |
| Weapons | 3 slots max, 4 weapon types, 10 upgrade levels each |
| Win | Kill boss or survive to tick 3840 (8 min) |

### Weapons

| Weapon | Type | Mechanic | Special |
|--------|------|----------|---------|
| Magic Wand | Auto-target | Fires at nearest enemy in range | Highest DPS |
| Axe | Arc projectile | Thrown with gravity physics | AoE damage |
| Whip | Directional melee | Strikes enemies in facing direction | Lifesteal: 3 HP per hit |
| Spell Books | Orbit | Rotating orbs damage on contact | Constant damage zone |

---

## RL Architecture

### Movement Agent (QLearningAgent)

Controls where the agent moves each tick using tabular Q-learning.

- **Actions:** UP, DOWN, LEFT, RIGHT, STAY (5 actions)
- **State:** 8-element tuple encoding enemy direction/distance, gem direction/distance, wall awareness, HP level
- **State space:** 3,888 unique states × 5 actions = 19,440 Q-table entries
- **Hyperparameters:** α=0.3, γ=0.95, ε decays from 0.5 → 0.06

### Weapon Choice Agent (WeaponChoiceAgent)

Decides which weapon to pick/upgrade on level-up. Evaluates each choice independently.

- **State:** 6-element tuple (HP bracket, wave, pressure, is_new, weapon_id, level_bracket)
- **State space:** 2,400 unique states
- **Update:** Delayed — all choices in an episode receive the terminal reward

---

## Project Structure

```
survival-game/
├── main.py                    # Entry point, game loop, mode select
│
├── game/
│   ├── config.py              # Constants, colors, MAP, hyperparameters
│   ├── agent.py               # Agent class (position, HP, movement)
│   ├── enemy.py               # Enemy class, spawn logic
│   ├── weapons.py             # Weapon definitions, scaling tables
│   ├── weapon_handlers.py     # Weapon behavior (wand, axe, whip+lifesteal, books)
│   ├── gems.py                # Gem/boss spawning, nearest gem distance
│   ├── level_up.py            # Level-up choice generation
│   ├── simulation.py          # Core game engine (run_tick), reward function
│   └── stats.py               # Per-episode and aggregate tracking
│
├── rl/
│   ├── q_tabular.py           # QLearningAgent + WeaponChoiceAgent
│   └── training.py            # Headless fast training loop
│
├── ui/
│   ├── effects.py             # Visual effects system
│   ├── rendering.py           # Map, fog, HUD, sprite rendering
│   ├── level_up_ui.py         # Manual mode weapon selection UI
│   └── results_screen.py      # Training results dashboard + export
│
├── analysis/
│   └── plots.py               # Matplotlib convergence plot
│
├── assets/                    # Sprites (player, enemy, boss, gem)
└── requirements.txt
```

---

## Key Results

| Metric | Start | Final | Target |
|--------|-------|-------|--------|
| Win Rate | 1.5% | 5.9% | 15% |
| Reward Improvement | — | +1,008 | Convergence ✓ |
| Avg Map Explored | 37% | 41% | 60% |
| Gem Approach % | 47% | 72% | 65% ✓ |
| Avg Player Level | 1.1 | 5.0 | 4 ✓ |

### Weapon Agent Learned Preferences

| Weapon | Pick Rate | Win Rate | HP Healed/Ep |
|--------|-----------|----------|-------------|
| Magic Wand | 52.2% | 23.2% | 0.0 |
| Axe | 38.9% | 13.6% | 0.0 |
| Spell Books | 36.3% | 12.6% | 0.0 |
| Whip | 32.2% | 10.2% | 8.9 |

### Learned Behavior (from diagnosis tool)

The agent learned HP-dependent behavior:
- **OK HP:** 58% chase gems, 42% flee from adjacent enemies
- **Critical HP:** 43% chase, 57% flee

---

## Training

### Fast Training (Headless)

Run the game, select Agent mode (1), press F. Training runs headlessly at full speed with no rendering.

Configuration in `game/config.py`:
- `MAX_EPISODES = 100000` — total training episodes
- `MAX_TICKS = 3840` — max ticks per episode
- `AGENT_MOVE_EVERY = 3` — movement cooldown

### Output Files

| File | Contents |
|------|----------|
| `reward_history.json` | Per-episode reward values |
| `run_stats.json` | Aggregate training statistics |
| `training_results.csv` | Exportable results (press D on results screen) |
| `results_screen.png` | Screenshot of results (press P on results screen) |

---

## References

Watkins, C. J. C. H., & Dayan, P. (1992). Q-learning. *Machine Learning*, 8(3–4), 279–292. https://doi.org/10.1007/BF00992698