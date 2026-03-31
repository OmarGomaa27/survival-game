import random
import math

# Weapon key -> integer id for state encoding
# Shield (id 4) is disabled but reserved for potential re-addition
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
           gem_dist_bucket,     # 0=near(≤3) 1=mid(4-6) 2=far(7+)
           wall_blocks_gem,     # 0=clear 1=wall blocks gem-x 2=blocks gem-y 3=both
           hp_bucket)           # 0=critical(≤25) 1=low(≤50) 2=ok
        """
        # -- Nearest enemy -----------------------------------------------------
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
                enemy_dist = 0    # adjacent — danger
            elif best_e <= 4:
                enemy_dist = 1    # close
            else:
                enemy_dist = 2    # medium
        else:
            ex = ey = 0
            enemy_dist = 3        # far / none

        # -- Nearest gem -------------------------------------------------------
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
                gem_dist = 0      # near
            elif best_g <= 6:
                gem_dist = 1      # medium
            else:
                gem_dist = 2      # far
        else:
            gx = gy = 0
            gem_dist = 2

        # ── Wall blocking gem direction (2 bits → 4 values) ──
        def blocked(dx, dy):
            nx, ny = agent.x + dx, agent.y + dy
            if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
                return True
            return self.game_map[ny][nx] == 1

        block_x = 1 if (gx != 0 and blocked(gx, 0)) else 0
        block_y = 1 if (gy != 0 and blocked(0, gy)) else 0
        wall_blocks_gem = block_x + block_y * 2  # 0=clear 1=x 2=y 3=both

        # ── HP bucket ─────────────────────────────────────────
        if agent.hp <= 25:
            hp_b = 0      # critical
        elif agent.hp <= 50:
            hp_b = 1      # low
        else:
            hp_b = 2      # ok

        return (ex, ey, enemy_dist,
                gx, gy, gem_dist,
                wall_blocks_gem,
                hp_b)


class WeaponChoiceAgent:
    """
    Separate Q-Learning agent that handles weapon selection on level up.

    State: (hp_bracket, wave_bracket, enemy_pressure,
            choice0_enc, choice1_enc, choice2_enc)

    Where each choice is encoded as:
        (is_new: 0/1, weapon_id: 0-4, current_level: 1-10)

    Actions: 0, 1, 2  (which card to pick)
    """

    def __init__(self, alpha=0.15, gamma=0.90,
                 epsilon=0.6, epsilon_decay=0.997, epsilon_min=0.10):
        self.alpha         = alpha
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min   = epsilon_min
        self.q_table       = {}
        self.actions       = [0, 1, 2]

        # Store ALL pending choices per episode (not just the last one)
        self._pending_choices = []  # list of (state, action)

    # ── Q helpers ─────────────────────────────────────────────
    def get_q(self, state, action):
        return self.q_table.get(state, {}).get(action, 0.0)

    def _set_q(self, state, action, value):
        if state not in self.q_table:
            self.q_table[state] = {}
        self.q_table[state][action] = value

    # ── State encoding ────────────────────────────────────────
    def encode_choice(self, kind, key, weapons):
        is_new    = 1 if kind == "new" else 0
        wid       = WEAPON_IDS.get(key, 0)
        cur_level = weapons[key]["level"] if key in weapons else 1
        return (is_new, wid, cur_level)

    def get_state(self, agent, enemies, weapons, wave, choices):
        # HP bracket
        if agent.hp > 66:   hp_b = 2
        elif agent.hp > 33: hp_b = 1
        else:               hp_b = 0

        # wave bracket (0-4)
        wave_b = min(wave // 3, 4)

        # enemy pressure (how many close enemies)
        close = sum(1 for e in enemies
                    if ((e.x-agent.x)**2+(e.y-agent.y)**2)**0.5 <= 5)
        pressure = min(close, 3)

        # encode each of the 3 choices
        encs = []
        for i in range(3):
            if i < len(choices):
                kind, key = choices[i]
                encs.append(self.encode_choice(kind, key, weapons))
            else:
                encs.append((0, 0, 1))   # padding

        return (hp_b, wave_b, pressure, *encs)

    # ── Decision ──────────────────────────────────────────────
    def choose(self, state, n_choices):
        valid = list(range(n_choices))
        if random.random() < self.epsilon:
            return random.choice(valid)
        qs = {a: self.get_q(state, a) for a in valid}
        return max(qs, key=qs.get)

    def record_choice(self, state, action):
        """Call right after making a weapon choice. Stores ALL choices
        made during an episode, not just the last one."""
        self._pending_choices.append((state, action))

    def update(self, reward, next_state=None):
        """Update Q-values for ALL weapon choices made this episode.
        Each choice receives the same episode reward signal, since
        we cannot attribute reward to individual weapon picks."""
        if not self._pending_choices:
            return

        for s, a in self._pending_choices:
            current_q = self.get_q(s, a)
            if next_state is not None:
                max_next = max(self.get_q(next_state, x) for x in self.actions)
            else:
                max_next = 0.0

            new_q = current_q + self.alpha * (
                        reward + self.gamma * max_next - current_q)
            self._set_q(s, a, new_q)

        self.epsilon = max(self.epsilon_min,
                           self.epsilon * self.epsilon_decay)

        self._pending_choices.clear()

    def has_pending(self):
        return len(self._pending_choices) > 0