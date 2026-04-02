import random
import math

# Weapon key -> integer id for state encoding
WEAPON_IDS = {"wand": 0, "axe": 1, "whip": 2, "books": 3, "shield": 4}


class QLearningAgent:
    """Handles movement decisions."""

    def __init__(self, actions, game_map=None, alpha=0.3, gamma=0.95,
                 epsilon=0.5, epsilon_decay=0.9997, epsilon_min=0.06):
        self.actions       = actions
        self.alpha         = alpha
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min   = epsilon_min
        self.q_table       = {}
        self.game_map      = game_map
        self.map_rows      = len(game_map) if game_map else 0
        self.map_cols      = len(game_map[0]) if game_map else 0

    def get_q(self, state, action):
        return self.q_table.get(state, {}).get(action, 0.0)

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        qs = {a: self.get_q(state, a) for a in self.actions}
        return max(qs, key=qs.get)

    def update(self, state, action, reward, next_state):
        current_q  = self.get_q(state, action)
        max_next_q = max(self.get_q(next_state, a) for a in self.actions)
        new_q      = current_q + self.alpha * (
                         reward + self.gamma * max_next_q - current_q)
        if state not in self.q_table:
            self.q_table[state] = {}
        self.q_table[state][action] = new_q
        self.epsilon = max(self.epsilon_min,
                           self.epsilon * self.epsilon_decay)

    def get_state(self, agent, enemies, gems):
        """
        State with directional wall awareness and distance buckets.

        Tuple (9 elements, ~3888 unique states):
          (ex, ey,              # direction to nearest enemy (-1/0/1)
           enemy_dist_bucket,   # 0=adjacent 1=close 2=medium 3=far/none
           gx, gy,              # direction to nearest gem (-1/0/1)
           gem_dist_bucket,     # 0=near(<=3) 1=mid(4-6) 2=far(7+)
           wall_blocks_gem,     # 0=clear 1=wall blocks gem-x 2=blocks gem-y 3=both
           hp_bucket)           # 0=critical(<=25) 1=low(<=50) 2=ok
        """
        nearest_enemy, best_e = None, float('inf')
        for e in enemies:
            d = ((e.x - agent.x)**2 + (e.y - agent.y)**2) ** 0.5
            if d < best_e:
                best_e, nearest_enemy = d, e

        if nearest_enemy and best_e <= 8:
            ex = int(math.copysign(1, nearest_enemy.x - agent.x)) \
                 if nearest_enemy.x != agent.x else 0
            ey = int(math.copysign(1, nearest_enemy.y - agent.y)) \
                 if nearest_enemy.y != agent.y else 0
            if best_e <= 2:
                enemy_dist = 0
            elif best_e <= 4:
                enemy_dist = 1
            else:
                enemy_dist = 2
        else:
            ex = ey = 0
            enemy_dist = 3

        nearest_gem, best_g = None, float('inf')
        for g in gems:
            d = abs(g[0] - agent.x) + abs(g[1] - agent.y)
            if d < best_g:
                best_g, nearest_gem = d, g

        if nearest_gem:
            gx = int(math.copysign(1, nearest_gem[0] - agent.x)) \
                 if nearest_gem[0] != agent.x else 0
            gy = int(math.copysign(1, nearest_gem[1] - agent.y)) \
                 if nearest_gem[1] != agent.y else 0
            if best_g <= 3:
                gem_dist = 0
            elif best_g <= 6:
                gem_dist = 1
            else:
                gem_dist = 2
        else:
            gx = gy = 0
            gem_dist = 2

        def blocked(dx, dy):
            nx, ny = agent.x + dx, agent.y + dy
            if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
                return True
            return self.game_map[ny][nx] == 1

        block_x = 1 if (gx != 0 and blocked(gx, 0)) else 0
        block_y = 1 if (gy != 0 and blocked(0, gy)) else 0
        wall_blocks_gem = block_x + block_y * 2

        if agent.hp <= 25:
            hp_b = 0
        elif agent.hp <= 50:
            hp_b = 1
        else:
            hp_b = 2

        return (ex, ey, enemy_dist,
                gx, gy, gem_dist,
                wall_blocks_gem,
                hp_b)


class WeaponChoiceAgent:
    """
    Weapon selection agent that evaluates each choice INDEPENDENTLY.

    Instead of learning "pick position 0/1/2" (which is meaningless
    when choices are shuffled), this agent scores each weapon option
    on its own merits:

        state = (hp_bracket, wave_bracket, pressure,
                 is_new, weapon_id, level_bracket)

    To decide: compute Q(state) for each of the 3 choices, pick highest.
    Now it's learning "Magic Wand upgrades are good when HP is high"
    instead of "click the left card."

    ~1440 possible states, each visited many times = actual learning.
    """

    def __init__(self, alpha=0.15, gamma=0.90,
                 epsilon=0.6, epsilon_decay=0.997, epsilon_min=0.10):
        self.alpha         = alpha
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min   = epsilon_min
        self.q_table       = {}

        self._pending_choices = []  # list of states that were picked

    # ── Q helpers ─────────────────────────────────────────────
    def get_q(self, state):
        return self.q_table.get(state, 0.0)

    def _set_q(self, state, value):
        self.q_table[state] = value

    # ── State encoding (per-choice) ──────────────────────────
    def _encode_context(self, agent, enemies, wave):
        if agent.hp > 66:   hp_b = 2
        elif agent.hp > 33: hp_b = 1
        else:               hp_b = 0

        wave_b = min(wave // 3, 4)

        close = sum(1 for e in enemies
                    if ((e.x - agent.x)**2 + (e.y - agent.y)**2)**0.5 <= 5)
        pressure = min(close, 3)

        return (hp_b, wave_b, pressure)

    def _encode_choice(self, kind, key, weapons):
        is_new = 1 if kind == "new" else 0
        wid    = WEAPON_IDS.get(key, 0)

        cur_level = weapons[key]["level"] if key in weapons else 0
        if cur_level == 0:
            lvl_b = 0   # new weapon
        elif cur_level <= 3:
            lvl_b = 1   # low
        elif cur_level <= 6:
            lvl_b = 2   # mid
        else:
            lvl_b = 3   # high

        return (is_new, wid, lvl_b)

    # ── Public API (called from main.py) ─────────────────────
    def get_state(self, agent, enemies, weapons, wave, choices):
        """Returns a list of per-choice states."""
        context = self._encode_context(agent, enemies, wave)
        states = []
        for kind, key in choices:
            enc = self._encode_choice(kind, key, weapons)
            states.append(context + enc)
        return states

    def choose(self, choice_states, n_choices):
        """Pick best choice by comparing independent Q-values."""
        if random.random() < self.epsilon:
            return random.choice(list(range(n_choices)))

        best_idx = 0
        best_q   = self.get_q(choice_states[0])
        for i in range(1, n_choices):
            q = self.get_q(choice_states[i])
            if q > best_q:
                best_q   = q
                best_idx = i
        return best_idx

    def record_choice(self, choice_states, picked_idx):
        """Record the picked choice's state for later update."""
        self._pending_choices.append(choice_states[picked_idx])

    def update(self, reward, next_state=None):
        """Update Q-values for ALL weapon choices made this episode."""
        if not self._pending_choices:
            return

        for s in self._pending_choices:
            current_q = self.get_q(s)
            new_q = current_q + self.alpha * (reward - current_q)
            self._set_q(s, new_q)

        self.epsilon = max(self.epsilon_min,
                           self.epsilon * self.epsilon_decay)
        self._pending_choices.clear()

    def has_pending(self):
        return len(self._pending_choices) > 0