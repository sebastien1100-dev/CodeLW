#!/usr/bin/env python3
"""Recopie les adversaires réels qui nous ont battus, pour les rejouer en scénario de test.

  python3 tools/opponents.py collect --days 3      # écrit tools/opponents.json

Chaque adversaire devient un poireau "inline" de scénario : mêmes stats finales (composants compris),
mêmes armes et puces. Leur vraie IA n'est pas accessible : ils sont pilotés par l'IA des bots "@expert".
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import lw  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "opponents.json")
STATS = ("life", "strength", "wisdom", "agility", "resistance", "science", "magic",
         "frequency", "tp", "mp", "cores", "ram")


def inline(leek_id):
    """Fiche publique d'un poireau -> entrée inline de scénario (None si illisible)."""
    l = lw.get(f"leek/get/{leek_id}")
    l = l.get("leek", l) if isinstance(l, dict) else {}
    if "total_life" not in l:
        return None
    entry = {"name": l["name"][:20], "level": l["level"], "ai": "@expert",
             "weapons": [lw.weapon_name(w["template"]) for w in l.get("weapons") or []],
             "chips": [lw.chip_name(c["template"]) for c in l.get("chips") or [] if str(c["template"]) in lw.chips()]}
    for k in STATS:
        entry[k] = max(1 if k in ("cores", "ram") else 0, l.get("total_" + k, 0))
    entry["_id"] = leek_id
    entry["_talent"] = l.get("talent")
    return entry


def collect(days, with_draws=False):
    hist = {}
    for x in lw.get(f"history/get-farmer-history/{lw.FARMER_ID}").get("fights", []):
        hist[x["id"]] = x
    for lid in lw.LEEKS.values():
        for x in lw.get(f"history/get-leek-history/{lid}").get("fights", []):
            hist[x["id"]] = x
    now = time.time()
    solo, teams, seen = [], [], {}
    for x in hist.values():
        if now - x["date"] > days * 86400 or x["context"] != 2 or x["type"] not in (0, 1):
            continue
        ids1 = [l["id"] if isinstance(l, dict) else l for l in x["leeks1"]]
        ids2 = [l["id"] if isinstance(l, dict) else l for l in x["leeks2"]]
        side = 1 if any(i in lw.LEEKS.values() for i in ids1) else 2
        if x["winner"] == side or (x["winner"] == 0 and not with_draws):
            continue  # on garde les défaites (et les nuls si demandé)
        opp_ids = ids2 if side == 1 else ids1
        entries = []
        for i in opp_ids:
            if i not in seen:
                seen[i] = inline(i)
            if seen[i]:
                entries.append(seen[i])
        if x["type"] == 0 and entries:
            solo.append({"fight": x["id"], "vs": [n for n, v in lw.LEEKS.items() if v in ids1 + ids2][0], "opp": entries[0]})
        elif x["type"] == 1 and len(entries) == len(opp_ids):
            teams.append({"fight": x["id"], "opp": entries})
    with open(OUT, "w") as f:
        json.dump({"collected": time.strftime("%Y-%m-%d %H:%M"), "days": days, "solo": solo, "teams": teams},
                  f, indent=1, ensure_ascii=False)
    print(f"{len(solo)} adversaires solo et {len(teams)} équipes (4 contre 4) -> {OUT}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("collect")
    s.add_argument("--days", type=int, default=3)
    s.add_argument("--draws", action="store_true", help="inclure aussi les matchs nuls")
    args = p.parse_args()
    collect(args.days, args.draws)


if __name__ == "__main__":
    main()
