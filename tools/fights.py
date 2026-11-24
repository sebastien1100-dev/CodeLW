#!/usr/bin/env python3
"""Combats réels du potager (consomment les combats du jour) et bilan.

  python3 tools/fights.py launch --solo 10 --farmer 70   # 10 solos par poireau + 70 combats d'éleveur
  python3 tools/fights.py report                           # résultats des combats lancés par ce script
  python3 tools/fights.py boss --boss 3                    # 1 combat de boss avec les 4 poireaux + butin obtenu

Les combats de boss consomment les combats du jour (même compteur que les combats solo/éleveur).

Les adversaires sont tirés au hasard parmi ceux proposés par le site (comme un clic dans le potager).
Le lancement par lots du site demande LW+ : on lance donc les combats un par un.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lw  # noqa: E402

LOG = os.path.join(lw.CACHE, "fights_log.json")


def load_log():
    if os.path.exists(LOG):
        with open(LOG) as f:
            return json.load(f)
    return []


def save_log(log):
    os.makedirs(lw.CACHE, exist_ok=True)
    with open(LOG, "w") as f:
        json.dump(log, f)


def launch(solo, farmer):
    log = load_log()
    remaining = lw.get("garden/get")["garden"]["fights"]
    print("combats disponibles :", remaining)
    todo = [("solo", n, lid) for _ in range(solo) for n, lid in lw.LEEKS.items()] + [("farmer", "éleveur", None)] * farmer
    for mode, name, lid in todo[:remaining]:
        for _attempt in range(3):  # l'adversaire peut avoir quitté le potager entre-temps
            if mode == "solo":
                ops = lw.get(f"garden/get-leek-opponents/{lid}").get("opponents", [])
                o = random.choice(ops)
                r = lw.api("POST", "garden/start-solo-fight", leek_id=lid, target_id=o["id"])
            else:
                ops = lw.get("garden/get-farmer-opponents").get("opponents", [])
                o = random.choice(ops)
                r = lw.api("POST", "garden/start-farmer-fight", target_id=o["id"])
            if isinstance(r, dict) and "fight" in r:
                log.append({"fight": r["fight"], "mode": mode, "name": name, "opp": o["name"], "opp_talent": o.get("talent")})
                break
    save_log(log)
    print("lancés :", sum(1 for e in log if "result" not in e))


def report():
    log = load_log()
    stats = {}
    errors = {}
    for e in log:
        if "result" not in e:
            r = lw.wait_fight(e["fight"])
            if not r:
                continue
            mine = 1 if any(l.get("farmer") == lw.FARMER_ID for l in r["leeks1"]) else 2
            e["result"] = "N" if r["winner"] == 0 else ("V" if r["winner"] == mine else "D")
            e["errors"] = lw.ai_errors(e["fight"])
        s = stats.setdefault(e["name"], {"V": 0, "D": 0, "N": 0})
        s[e["result"]] += 1
        for k, n in e.get("errors", {}).items():
            errors[k] = errors.get(k, 0) + n
    save_log(log)
    for name, s in stats.items():
        n = sum(s.values())
        print(f"{name:9} V{s['V']} D{s['D']} N{s['N']}  ({100 * s['V'] // max(1, n)}%)")
    print("erreurs IA :", errors or "aucune")
    f = lw.get("farmer/get-from-token")["farmer"]
    print("talent éleveur", f["talent"], "|", ", ".join(f"{l['name']} {l['talent']}" for l in f["leeks"].values()))


def inventory():
    f = lw.get("farmer/get-from-token")["farmer"]
    inv = {}
    for kind in ("resources", "components", "chips", "weapons", "potions", "schemes", "hats"):
        for r in f.get(kind) or []:
            inv[r["template"]] = inv.get(r["template"], 0) + r["quantity"]
    return f["habs"], f.get("crystals", 0), inv


def boss(boss_id):
    import resources  # données du jeu (noms des objets)
    items = resources.game_data()["items"]
    habs0, cry0, inv0 = inventory()
    r = lw.api("POST", "garden/start-boss-fight", boss_id=boss_id, participants=json.dumps(list(lw.LEEKS.values())))
    if not isinstance(r, dict) or "fight" not in r:
        print("combat de boss impossible :", r)
        return
    f = lw.wait_fight(r["fight"], tries=60)
    mine = 1 if f and any(l.get("farmer") == lw.FARMER_ID for l in f["leeks1"]) else 2
    result = "?" if not f else ("nul" if f["winner"] == 0 else ("victoire" if f["winner"] == mine else "défaite"))
    habs1, cry1, inv1 = inventory()
    loot = {items.get(str(t), {}).get("name", str(t)): inv1.get(t, 0) - inv0.get(t, 0)
            for t in set(inv0) | set(inv1) if inv1.get(t, 0) != inv0.get(t, 0)}
    print(f"boss {boss_id} : {result} (combat {r['fight']}) | habs {habs1 - habs0:+d} | cristaux {cry1 - cry0:+d}")
    print("butin :", loot or "rien")
    print("erreurs IA :", lw.ai_errors(r["fight"]) or "aucune")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("launch")
    s.add_argument("--solo", type=int, default=0, help="combats solo par poireau")
    s.add_argument("--farmer", type=int, default=0, help="combats d'éleveur (4 contre 4)")
    sub.add_parser("report")
    s = sub.add_parser("boss")
    s.add_argument("--boss", type=int, default=3, help="1 nasu_samurai (niv 100), 2 fennel_king (200), 3 evil_pumpkin (300), 1023 fennel_pumpkin (300)")
    args = p.parse_args()
    if args.cmd == "launch":
        launch(args.solo, args.farmer)
    elif args.cmd == "boss":
        boss(args.boss)
    else:
        report()


if __name__ == "__main__":
    main()
