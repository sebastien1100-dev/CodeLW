#!/usr/bin/env python3
"""Combats réels du potager (consomment les combats du jour) et bilan.

  python3 tools/fights.py launch --solo 10 --farmer 70   # 10 solos par poireau + 70 combats d'éleveur
  python3 tools/fights.py report                           # résultats des combats lancés par ce script

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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("launch")
    s.add_argument("--solo", type=int, default=0, help="combats solo par poireau")
    s.add_argument("--farmer", type=int, default=0, help="combats d'éleveur (4 contre 4)")
    sub.add_parser("report")
    args = p.parse_args()
    if args.cmd == "launch":
        launch(args.solo, args.farmer)
    else:
        report()


if __name__ == "__main__":
    main()
