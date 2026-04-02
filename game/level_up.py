import random
from game.config import MAX_WEAPON_SLOTS
from game.weapons import WEAPON_POOL, apply_level_up


def generate_level_up_choices(weapons):
    owned_keys   = list(weapons.keys())
    unowned_keys = [k for k in WEAPON_POOL if k not in weapons]
    empty_slots  = MAX_WEAPON_SLOTS - len(weapons)
    pool = []
    if empty_slots > 0 and unowned_keys:
        new_picks = random.sample(unowned_keys, min(len(unowned_keys), 2))
        pool += [("new", k) for k in new_picks]
    upgradeable = [k for k in owned_keys if weapons[k]["level"] < 10]
    if upgradeable:
        pool += [("upgrade", k)
                 for k in random.sample(upgradeable, min(len(upgradeable), 3))]
    random.shuffle(pool)
    seen, choices = set(), []
    for item in pool:
        if item not in seen and len(choices) < 3:
            seen.add(item)
            choices.append(item)
    while len(choices) < 3 and upgradeable:
        fallback = [("upgrade", k) for k in upgradeable
                    if ("upgrade", k) not in choices]
        if not fallback:
            break
        choices.append(random.choice(fallback))
    return choices


def apply_choice(choice, weapons):
    kind, key = choice
    if kind == "new":
        weapons[key] = {k: (list(v) if isinstance(v, list) else v)
                        for k, v in WEAPON_POOL[key].items()}
    elif kind == "upgrade" and key in weapons:
        apply_level_up(key, weapons[key])
