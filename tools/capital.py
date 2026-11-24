"""Barème du capital Leek Wars (repris du client du site) et conversion achats <-> stats."""

STEPS = {
    "life": [(0, 1, 4), (1000, 1, 3), (2000, 1, 2)],            # (à partir de N achetés, coût, gain)
    "stat": [(0, 1, 2), (200, 1, 1), (400, 2, 1), (600, 3, 1)],  # force, sagesse, agilité, résistance, science, magie
    "frequency": [(0, 1, 1)],
    "tp": [(i, 30 + 5 * i, 1) for i in range(15)],
    "mp": [(i, 20 + 20 * i, 1) for i in range(9)],
}
BASE = {"frequency": 100, "tp": 10, "mp": 3, "cores": 1, "ram": 6}


def _table(stat):
    return STEPS.get(stat, STEPS["stat"])


def cost(stat, bought):
    """Capital nécessaire pour acheter `bought` points de `stat`."""
    table, c, b = _table(stat), 0, 0
    while b < bought:
        step = [s for s in table if s[0] <= b][-1]
        c += step[1]
        b += step[2]
    return c


def buy(stat, capital):
    """Points de `stat` obtenus avec au plus `capital`. Renvoie (points, capital dépensé)."""
    table, b, c = _table(stat), 0, 0
    while True:
        step = [s for s in table if s[0] <= b][-1]
        if c + step[1] > capital:
            return b, c
        c += step[1]
        b += step[2]


def base_life(level):
    return 100 + 3 * (level - 1)


def total_capital(level):
    """Capital total d'un poireau (vérifié sur les poireaux du compte : 1680 au niv. 300, 1780 au 301)."""
    return 1780 if level >= 301 else 1680


def build_stats(bought, level, fill_life=True):
    """Achats -> stats finales (hors composants). Complète en vie avec le capital restant si demandé."""
    bought = dict(bought)
    spent = sum(cost(k, v) for k, v in bought.items())
    if fill_life and "life" not in bought:
        bought["life"], used = buy("life", total_capital(level) - spent)
        spent += used
    stats = {k: bought.get(k, 0) for k in ("strength", "wisdom", "agility", "resistance", "science", "magic")}
    stats["life"] = base_life(level) + bought.get("life", 0)
    for k, v in BASE.items():
        stats[k] = v + bought.get(k, 0)
    return stats, bought, spent
