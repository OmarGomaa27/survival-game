class EpisodeStats:
    """Tracks stats for a single episode."""
    def __init__(self):
        self.ticks        = 0
        self.boss_kills   = 0
        self.player_level = 1
        self.won          = False   # survived to MAX_TICKS

        # per weapon key -> damage dealt this episode
        self.weapon_damage  = {}   # key -> total damage
        self.weapon_level   = {}   # key -> final level at episode end
        self.weapon_present = set()
        self.hp_saved       = {}   # key -> total HP saved this episode
        self.hp_healed = {}   # key -> total HP healed this episode

        # Diagnostics
        self.gems_collected   = 0
        self.damage_taken     = 0
        self.hits_taken       = 0
        self.moves_toward_gem = 0
        self.moves_away_gem   = 0
        self.moves_total      = 0
        self.tiles_revealed   = 0
        self.boss_win         = False
        

        # weapon choice tracking
        self.weapon_choices   = []  # list of (choices, weights, picked_idx)

    def record_damage(self, weapon_key, damage):
        self.weapon_damage[weapon_key] = \
            self.weapon_damage.get(weapon_key, 0) + damage

    def record_block(self, weapon_key, damage_blocked):
        self.hp_saved[weapon_key] = \
            self.hp_saved.get(weapon_key, 0) + damage_blocked
        
    def record_heal(self, weapon_key, amount):
        self.hp_healed[weapon_key] = \
            self.hp_healed.get(weapon_key, 0) + amount

    def record_weapon_state(self, weapons):
        for key, w in weapons.items():
            self.weapon_present.add(key)
            self.weapon_level[key] = w["level"]

    def record_hit(self, damage):
        self.hits_taken   += 1
        self.damage_taken += damage

    def record_gem(self):
        self.gems_collected += 1

    def record_move(self, toward_gem):
        """toward_gem: True if agent moved closer, False if farther, None if no change."""
        self.moves_total += 1
        if toward_gem is True:
            self.moves_toward_gem += 1
        elif toward_gem is False:
            self.moves_away_gem += 1

    def gem_approach_ratio(self):
        directed = self.moves_toward_gem + self.moves_away_gem
        if directed == 0:
            return 0.0
        return self.moves_toward_gem / directed

    def dps(self, weapon_key):
        """Damage per tick (use ticks as time unit)."""
        if self.ticks == 0:
            return 0.0
        return self.weapon_damage.get(weapon_key, 0) / self.ticks


class RunTracker:
    """
    Aggregates stats across all episodes.
    Call .start_episode() at the beginning of each run,
    update fields during the run, then .end_episode() when done.
    """
    def __init__(self):
        self.episodes         = 0
        self.wins             = 0
        self.boss_kills_total = 0
        self.max_player_level = 1

        self._weapon_episodes    = {}   # key -> episodes appeared in
        self._weapon_wins        = {}   # key -> wins when present
        self._weapon_level_sum   = {}   # key -> sum of final levels
        self._weapon_dps_sum     = {}   # key -> sum of dps values
        self._weapon_dps_max     = {}   # key -> max dps ever seen
        self._weapon_hp_saved_sum = {}  # key -> total HP saved across episodes
        self._weapon_hp_healed_sum = {} # key -> total HP healed across episodes
        self._player_level_sum   = 0

        # Diagnostic accumulators
        self._ticks_sum           = 0
        self._gems_sum            = 0
        self._damage_taken_sum    = 0
        self._hits_taken_sum      = 0
        self._toward_sum          = 0
        self._away_sum            = 0
        self._moves_sum           = 0
        self._tiles_revealed_sum  = 0
        self._boss_wins           = 0
        self._gems_at_death_hist  = {}  # gems_collected -> count

        # Weapon choice diagnostics
        self._total_levelups      = 0
        self._choice_picks        = {}  # (kind, key) -> times picked
        self._choice_offered      = {}  # (kind, key) -> times offered
        self._choice_weights_sum  = {}  # key -> sum of weights when offered
        self._choice_weights_n    = {}  # key -> count of times offered

        self._current = None

    def start_episode(self):
        self._current = EpisodeStats()
        return self._current
    
    def weapon_avg_hp_healed(self, key):
        n = self._weapon_episodes.get(key, 0)
        return self._weapon_hp_healed_sum.get(key, 0.0) / max(n, 1)

    def end_episode(self, won=False):
        ep = self._current
        if ep is None:
            return
        ep.won = won
        self.episodes += 1
        if won:
            self.wins += 1
        self.boss_kills_total += ep.boss_kills
        self.max_player_level  = max(self.max_player_level, ep.player_level)
        self._player_level_sum += ep.player_level

        # diagnostics
        self._ticks_sum        += ep.ticks
        self._gems_sum         += ep.gems_collected
        self._damage_taken_sum += ep.damage_taken
        self._hits_taken_sum   += ep.hits_taken
        self._toward_sum       += ep.moves_toward_gem
        self._away_sum         += ep.moves_away_gem
        self._moves_sum        += ep.moves_total
        self._tiles_revealed_sum += ep.tiles_revealed
        if ep.boss_win:
            self._boss_wins += 1

        # weapon choice diagnostics
        for choices, weights, picked_idx in ep.weapon_choices:
            self._total_levelups += 1
            for i, (kind, key) in enumerate(choices):
                ck = (kind, key)
                self._choice_offered[ck] = self._choice_offered.get(ck, 0) + 1
                self._choice_weights_sum[key] = \
                    self._choice_weights_sum.get(key, 0.0) + weights[i]
                self._choice_weights_n[key] = \
                    self._choice_weights_n.get(key, 0) + 1
                if i == picked_idx:
                    self._choice_picks[ck] = self._choice_picks.get(ck, 0) + 1

        gc = ep.gems_collected
        self._gems_at_death_hist[gc] = self._gems_at_death_hist.get(gc, 0) + 1

        for key in ep.weapon_present:
            self._weapon_episodes[key]  = self._weapon_episodes.get(key,  0) + 1
            self._weapon_level_sum[key] = self._weapon_level_sum.get(key, 0) + \
                                          ep.weapon_level.get(key, 1)
            self._weapon_hp_saved_sum[key] = \
                self._weapon_hp_saved_sum.get(key, 0) + \
                ep.hp_saved.get(key, 0)
            self._weapon_hp_healed_sum[key] = \
                self._weapon_hp_healed_sum.get(key, 0) + \
                ep.hp_healed.get(key, 0)
            if won:
                self._weapon_wins[key] = self._weapon_wins.get(key, 0) + 1

            dps = ep.dps(key)
            self._weapon_dps_sum[key] = self._weapon_dps_sum.get(key, 0.0) + dps
            self._weapon_dps_max[key] = max(
                self._weapon_dps_max.get(key, 0.0), dps)

        self._current = None

    # -- Aggregated getters -------------------------------------------------
    def win_rate(self):
        return self.wins / max(self.episodes, 1)

    def avg_player_level(self):
        return self._player_level_sum / max(self.episodes, 1)

    def avg_ticks(self):
        return self._ticks_sum / max(self.episodes, 1)

    def avg_gems(self):
        return self._gems_sum / max(self.episodes, 1)

    def avg_damage_taken(self):
        return self._damage_taken_sum / max(self.episodes, 1)

    def avg_hits_taken(self):
        return self._hits_taken_sum / max(self.episodes, 1)

    def gem_approach_ratio(self):
        directed = self._toward_sum + self._away_sum
        if directed == 0:
            return 0.0
        return self._toward_sum / directed

    def avg_tiles_revealed(self):
        return self._tiles_revealed_sum / max(self.episodes, 1)

    def boss_win_count(self):
        return self._boss_wins

    def total_levelups(self):
        return self._total_levelups

    def choice_summary(self):
        """Returns list of dicts for display: key, offered, picked_new,
        picked_upgrade, avg_weight."""
        all_keys = set()
        for (kind, key) in self._choice_offered:
            all_keys.add(key)
        summary = []
        for key in sorted(all_keys):
            offered = (self._choice_offered.get(("new", key), 0) +
                       self._choice_offered.get(("upgrade", key), 0))
            picked_new = self._choice_picks.get(("new", key), 0)
            picked_up  = self._choice_picks.get(("upgrade", key), 0)
            n = self._choice_weights_n.get(key, 0)
            avg_w = (self._choice_weights_sum.get(key, 0.0) / n) if n > 0 else 0.0
            summary.append({
                "key": key, "offered": offered,
                "picked_new": picked_new, "picked_upgrade": picked_up,
                "picked_total": picked_new + picked_up,
                "avg_weight": avg_w,
            })
        return summary

    def gems_at_death_histogram(self):
        """Returns sorted list of (gems_collected, count)."""
        return sorted(self._gems_at_death_hist.items())

    def pct_reaching_n_gems(self, n):
        """What % of episodes collected at least n gems."""
        reached = sum(c for g, c in self._gems_at_death_hist.items() if g >= n)
        return reached / max(self.episodes, 1)

    def weapon_avg_dps(self, key):
        n = self._weapon_episodes.get(key, 0)
        return self._weapon_dps_sum.get(key, 0.0) / max(n, 1)

    def weapon_max_dps(self, key):
        return self._weapon_dps_max.get(key, 0.0)

    def weapon_win_rate(self, key):
        n = self._weapon_episodes.get(key, 0)
        w = self._weapon_wins.get(key, 0)
        return w / max(n, 1)

    def weapon_avg_level(self, key):
        n = self._weapon_episodes.get(key, 0)
        return self._weapon_level_sum.get(key, 0) / max(n, 1)

    def weapon_avg_hp_saved(self, key):
        n = self._weapon_episodes.get(key, 0)
        return self._weapon_hp_saved_sum.get(key, 0.0) / max(n, 1)

    def weapon_appearances(self, key):
        return self._weapon_episodes.get(key, 0)

    def all_weapon_keys(self):
        return sorted(self._weapon_episodes.keys())

    def summary_dict(self):
        return {
            "episodes":         self.episodes,
            "wins":             self.wins,
            "win_rate":         self.win_rate(),
            "boss_kills_total": self.boss_kills_total,
            "max_player_level": self.max_player_level,
            "avg_player_level": self.avg_player_level(),
            "avg_ticks":        self.avg_ticks(),
            "avg_gems":         self.avg_gems(),
            "avg_damage_taken": self.avg_damage_taken(),
            "avg_hits_taken":   self.avg_hits_taken(),
            "gem_approach_ratio": self.gem_approach_ratio(),
            "avg_tiles_revealed": self.avg_tiles_revealed(),
            "boss_wins":         self._boss_wins,
            "total_levelups":    self._total_levelups,
            "weapon_choices":    self.choice_summary(),
            "pct_reaching_5_gems": self.pct_reaching_n_gems(5),
            "gems_histogram":   self.gems_at_death_histogram(),
            "weapons":          {
                key: {
                    "appearances": self.weapon_appearances(key),
                    "avg_dps":     self.weapon_avg_dps(key),
                    "max_dps":     self.weapon_max_dps(key),
                    "win_rate":    self.weapon_win_rate(key),
                    "avg_level":   self.weapon_avg_level(key),
                    "avg_hp_saved": self.weapon_avg_hp_saved(key),
                }
                for key in self.all_weapon_keys()
            }
        }