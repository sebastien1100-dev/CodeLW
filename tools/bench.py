#!/usr/bin/env python3
"""Bancs de test Leek Wars, via les scénarios de test (combats gratuits et illimités).

Exemples :
  # Kador (vraie fiche) avec l'IA OptiDev contre sebo, jessy et Enzo, 8 graines x 2 côtés
  python3 tools/bench.py duel --hero Kador --ai OptiDev --opps sebo,jessy,Enzo --seeds 8

  # comparaison A/B de deux IA sur exactement les mêmes combats
  python3 tools/bench.py ab --hero Kador --ai Opti --ai2 OptiDev --opps sebo,jessy,Enzo --seeds 8

  # clone de Kador avec une autre répartition de capital (tools/builds.json)
  python3 tools/bench.py duel --hero Kador --build equilibre --opps sebo,jessy,Enzo --seeds 8

  # Kador avec un autre équipement (tools/kits.json)
  python3 tools/bench.py duel --hero Kador --kit kitC --opps Enzo --seeds 15

  # 4 contre 4 : nos poireaux contre les bots "expert"
  python3 tools/bench.py team --ai Opti --seeds 6

  # envoyer un fichier d'IA du dépôt sur Leek Wars
  python3 tools/bench.py upload ais/Opti.leek --as OptiDev

Méthode : chaque graine est jouée des deux côtés de la carte. Un écart de moins de ~10 points
sur 48 combats est du bruit ; refaire une série avec --seed0 différent avant de conclure.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lw  # noqa: E402
import capital  # noqa: E402

HERE = os.path.dirname(__file__)
STATS = ("life", "strength", "wisdom", "agility", "resistance", "science", "magic",
         "frequency", "tp", "mp", "cores", "ram")


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


def opponent(o, ai):
    if o in lw.BOTS:
        return {"bot": o, "ai": "@expert"}
    return {"leek": o, "ai": ai}


def hero_entry(args, ai):
    lid = lw.LEEKS[args.hero]
    if args.build:
        # clone "inline" : mêmes armes/puces, stats recalculées depuis le capital, bonus de composants conservés
        l = lw.leek(lid)
        stats, bought, spent = capital.build_stats(load("builds.json")[args.build], l["level"])
        for k in STATS:  # bonus des composants = total - base achetée
            stats[k] += l["total_" + k] - l[k]
        lo = lw.loadout(lid)
        entry = {"name": (args.hero + "_" + args.build)[:20], "level": l["level"], "ai": ai,
                 "weapons": lo["weapons"], "chips": lo["chips"], **stats}
        print(f"  build {args.build} : capital {spent}/{capital.total_capital(l['level'])} -> "
              + ", ".join(f"{k} {stats[k]}" for k in ("life", "strength", "wisdom", "resistance", "agility", "tp", "mp")))
        return entry
    entry = {"leek": args.hero, "ai": ai}
    if args.kit:
        kit = dict(load("kits.json")[args.kit])
        kit.setdefault("components", lw.loadout(lid)["components"])  # sans composants : 1 cœur, l'IA plante
        entry["loadout"] = kit
    return entry


def score(fights, side_of):
    w = l = d = 0
    errors = {}
    for fid, sc in fights:
        r = lw.wait_fight(fid)
        if not r or "winner" not in r:
            continue
        side = side_of(sc)
        if r["winner"] == 0:
            d += 1
        elif r["winner"] == side:
            w += 1
        else:
            l += 1
        for k, n in lw.ai_errors(fid).items():
            errors[k] = errors.get(k, 0) + n
    n = w + l + d
    return w, l, d, n, errors


def report(label, res):
    w, l, d, n, errors = res
    pct = 100 * w // max(1, n)
    print(f"{label} : V{w} D{l} N{d} sur {n} ({pct}%)" + (f"  erreurs IA={errors}" if errors else ""))


def duel(args, ai):
    me = hero_entry(args, ai)
    opps = [o for o in args.opps.split(",") if o != args.hero]
    scenarios = []
    for seed in range(args.seed0, args.seed0 + args.seeds):
        for o in opps:
            for swap in (0, 1):
                t1, t2 = [me], [opponent(o, args.opp_ai)]
                if swap:
                    t1, t2 = t2, t1
                scenarios.append({"type": "leek-wars-scenario", "version": 1, "fight": "solo",
                                  "seed": seed * 7919 + len(o) * 13, "team1": t1, "team2": t2,
                                  "_hero_team": 2 if swap else 1})
    fights = lw.run_scenarios(scenarios, args.path)
    return score(fights, lambda sc: sc["_hero_team"])


def team(args):
    mine = [{"leek": n, "ai": args.ai} for n in lw.LEEKS]
    bots = [{"bot": b, "ai": "@expert"} for b in lw.BOTS[:4]]
    scenarios = []
    for seed in range(args.seed0, args.seed0 + args.seeds):
        for swap in (0, 1):
            t1, t2 = (bots, mine) if swap else (mine, bots)
            scenarios.append({"type": "leek-wars-scenario", "version": 1, "fight": "farmer",
                              "seed": seed * 104729, "team1": t1, "team2": t2, "_hero_team": 2 if swap else 1})
    fights = lw.run_scenarios(scenarios, args.path)
    return score(fights, lambda sc: sc["_hero_team"])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("duel", "ab"):
        s = sub.add_parser(name)
        s.add_argument("--hero", required=True, choices=list(lw.LEEKS))
        s.add_argument("--ai", default="Opti")
        if name == "ab":
            s.add_argument("--ai2", required=True)
        s.add_argument("--opp-ai", default="Opti", help="IA de nos poireaux adverses")
        s.add_argument("--opps", default="sebo,jessy,Enzo,Kador", help="poireaux du compte et/ou bots, séparés par des virgules")
        s.add_argument("--kit", help="équipement de tools/kits.json")
        s.add_argument("--build", help="répartition de capital de tools/builds.json (clone inline)")
    s = sub.add_parser("team")
    s.add_argument("--ai", default="Opti")
    s = sub.add_parser("upload")
    s.add_argument("file")
    s.add_argument("--as", dest="target", required=True, help="chemin du fichier sur Leek Wars")
    for s in sub.choices.values():
        if s.prog.split()[-1] != "upload":
            s.add_argument("--seeds", type=int, default=8)
            s.add_argument("--seed0", type=int, default=1)
            s.add_argument("--path", default="test_scenario.json", help="fichier de scénario (un par banc parallèle)")
    args = p.parse_args()

    if args.cmd == "upload":
        with open(args.file) as f:
            problems = lw.upload_ai(args.target, f.read())
        print("compilé sans erreur" if problems == [] else problems)
    elif args.cmd == "duel":
        report(f"{args.hero} [{args.ai}]", duel(args, args.ai))
    elif args.cmd == "ab":
        report(f"{args.hero} [{args.ai}]", duel(args, args.ai))
        report(f"{args.hero} [{args.ai2}]", duel(args, args.ai2))
    elif args.cmd == "team":
        report(f"4c4 [{args.ai}] contre bots", team(args))


if __name__ == "__main__":
    main()
