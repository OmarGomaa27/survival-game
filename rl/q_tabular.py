import random
import math

# Weapon key -> integer id for state encoding
WEAPON_IDS = {"wand": 0, "axe": 1, "whip": 2, "books": 3, "shield": 4}


class QLearningAgent:
    """Handles movement decisions."""

    def __init__(self, actions, game_map=None, alpha=0.1, gamma=0.95, 
                 epsilon=0.5, epsilon_decay=0.9997, epsilon_min=0.06): 
        self.actions       = actions #UP, DOWN, LEFT, RIGHT, STAY
        self.alpha         = alpha # learning rate (how much new info overrides old) [0.0-1.0]
        self.gamma         = gamma # discount factor (how much future rewards are worth compared to immediate) [0.0-1.0]
        self.epsilon       = epsilon # exploration rate (chance to pick random action instead of best known) [0.0-1.0]
        self.epsilon_decay = epsilon_decay # how much to decay epsilon after each update (e.g. 0.999 means 0.1% decay per update)
        self.epsilon_min   = epsilon_min # minimum exploration rate (0.06 means never stop exploring entirely. Always try random stuff 6% of the time.)
        self.q_table       = {} # state -> action -> Q-value
        self.game_map      = game_map # 2D list of 0/1 for free/wall, used for state encoding
        self.map_rows      = len(game_map) if game_map else 0 # number of rows in the map, used for state encoding
        self.map_cols      = len(game_map[0]) if game_map else 0 # number of columns in the map, used for state encoding

    def get_q(self, state, action): #Q-value for this state-action pair?" If we've never seen it, return 0.0 (optimistic — assumes unknown actions are worth trying)
        return self.q_table.get(state, {}).get(action, 0.0) # default Q-value is 0.0 for unseen state-action pairs

    def choose_action(self, state): # Epsilon-greedy action selection: with probability epsilon, pick random action; 
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        qs = {a: self.get_q(state, a) for a in self.actions} #otherwise, pick the action with the highest Q-value for this state
        return max(qs, key=qs.get)
    
 # Watkins & Dayan update rule
 # state s, did action a, got reward r, and ended up in state s'. The best future value from s' is max_next_q. 
 # The real value of doing a in s is approximately r + γ * max_next_q. 
 # Nudge old estimate toward that real value by alpha

    def update(self, state, action, reward, next_state): # Q-learning update rule: Q(s,a) = Q(s,a) + alpha * (reward + gamma * max_a' Q(s',a') - Q(s,a))
        current_q  = self.get_q(state, action)                                   # Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') - Q(s,a)]
        max_next_q = max(self.get_q(next_state, a) for a in self.actions)
        new_q      = current_q + self.alpha * (
                         reward + self.gamma * max_next_q - current_q)
        if state not in self.q_table: # If we've never seen this state before, initialize it in the Q-table
            self.q_table[state] = {} # update the Q-value for this state-action pair
        self.q_table[state][action] = new_q #
        self.epsilon = max(self.epsilon_min,
                           self.epsilon * self.epsilon_decay) # Decay epsilon after each update, but never go below epsilon_min

    def get_state(self, agent, enemies, gems): # game world is compressed into a discrete state representation that captures important info 
                                               # for decision-making, while ignoring irrelevant details.
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
            dx = e.x - agent.x
            dy = e.y - agent.y
            d2 = dx*dx + dy*dy
            if d2 < best_e:
                best_e, nearest_enemy = d2, e

        if nearest_enemy and best_e <= 64:
            ex = int(math.copysign(1, nearest_enemy.x - agent.x)) \
                 if nearest_enemy.x != agent.x else 0
            ey = int(math.copysign(1, nearest_enemy.y - agent.y)) \
                 if nearest_enemy.y != agent.y else 0
            if best_e <= 4:
                enemy_dist = 0
            elif best_e <= 16:
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

        def blocked(dx, dy): # Check if there's a wall in the direction of the gem. 
                             # This helps the agent learn to navigate around obstacles when trying to reach gems.
            nx, ny = agent.x + dx, agent.y + dy
            if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
                return True
            return self.game_map[ny][nx] == 1

        block_x = 1 if (gx != 0 and blocked(gx, 0)) else 0
        block_y = 1 if (gy != 0 and blocked(0, gy)) else 0
        wall_blocks_gem = block_x + block_y * 2

        if agent.hp <= 25: # HP bucket: 0=critical(<=25) 1=low(<=50) 2=ok
            hp_b = 0 # critical HP, be very cautious
        elif agent.hp <= 50: # low HP, be more cautious
            hp_b = 1
        else:
            hp_b = 2 # ok HP, can be more aggressive

        return (ex, ey, enemy_dist,
                gx, gy, gem_dist,
                wall_blocks_gem,
                hp_b)           # State is a tuple of 9 elements, with directional info, distance buckets, wall awareness, and HP bucket.
                                # ex, ey: direction to nearest enemy. Each is -1, 0, or 1. (3 × 3 = 9 combos)
                                # enemy_dist: 0=adjacent, 1=close, 2=medium, 3=far. (4 options)
                                # gx, gy: direction to nearest gem. Each is -1, 0, or 1. (3 × 3 = 9 combos)
                                # gem_dist: 0=near(<=3), 1=mid(4-6), 2=far(7+). (3 options)
                                # wall_blocks_ge    m: 0=clear, 1=wall blocks gem-x, 2=blocks gem-y, 3=both. (4 options)
                                # hp_b: 0=critical(<=25), 1=low(<=50), 2=ok. (3 options)
                                # Total unique states: 9 (enemy dir) × 4 (enemy dist) × 9 (gem dir) × 3 (gem dist) × 4 (wall blocks) × 3 (HP bucket) = 3888 states



class WeaponChoiceAgent:
    """4
    Weapon selection agent that evaluates each choice INDEPENDENTLY.
    """
    # The movement agent acts every few ticks and gets immediate rewards. 
    # The weapon agent acts maybe once or twice per episode and only learns the outcome when the episode ends. 
    # It's a much harder learning problem — like evaluating whether a chess opening was good based on who won 50 moves later.

    def __init__(self, alpha=0.05, gamma=0.90,
                 epsilon=0.6, epsilon_decay=0.997, epsilon_min=0.10):   # alpha=learning rate, gamma=discount factor, 
                                                                        # epsilon=exploration rate, epsilon_decay=decay rate for exploration, 
                                                                        # epsilon_min=minimum exploration rate
        self.alpha         = alpha              # learning rate (how much new info overrides old) [0.0-1.0]
        self.gamma         = gamma              # discount factor (how much future rewards are worth compared to immediate) [0.0-1.0]
        self.epsilon       = epsilon            # exploration rate (chance to pick random action instead of best known) [0.0-1.0]
        self.epsilon_decay = epsilon_decay      # how much to decay epsilon after each update (e.g. 0.997 means 0.3% decay per update)
        self.epsilon_min   = epsilon_min        # minimum exploration rate (0.10 means never stop exploring entirely. 
                                                # Always try random stuff 10% of the time.)

        self.q_table       = {}                 # state -> Q-value (since we evaluate each choice independently, 
                                                # we only need state -> Q-value, not state -> action -> Q-value)

        self._pending_choices = []  # list of states that were picked # but not yet updated with a reward. 
                        
                                     # We wait until the end of the episode to update all of them with the final reward, 
                                    # since the reward is only given at the end and applies to all choices made during the episode.

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
                    if (e.x - agent.x) * (e.x - agent.x) + (e.y - agent.y) * (e.y - agent.y) <= 25)
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

    def choose(self, choice_states, n_choices): # Epsilon-greedy choice among the given options, based on their independent Q-values.
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