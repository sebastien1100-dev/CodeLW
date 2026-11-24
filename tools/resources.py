#!/usr/bin/env python3
"""Contrôle des ressources pour les composants utiles (PT, PM, cœurs, RAM).

  python3 tools/resources.py            # bilan : fabricable / ce qu'il manque, stock des ressources clés

Lecture seule : ne fabrique rien, n'ouvre rien. Les recettes et objets viennent des données du site
(page d'accueil, variable __DATA__), le stock de l'éleveur via l'API.
Attention : certaines "boîtes" (box_10k_habs, box_100k_habs) et les coffres sont des ingrédients ;
les ouvrir les détruit.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lw  # noqa: E402

# composants visés, du plus intéressant au moins intéressant
TARGETS = ["power_supply", "battery", "motherboard2", "motherboard3", "chestnut", "ssd", "pear",
           "core2", "core3", "propulsor2", "soursop", "elinvar_spring", "nuclear_core"]
KEY_RESOURCES = ["gold_nugget", "silver_nugget", "statuette", "hab", "lantern", "topaze", "raw_ruby",
                 "cornaline", "box_10k_habs", "box_100k_habs", "iron_chest", "wood_chest"]


def game_data():
    path = os.path.join(lw.CACHE, "gamedata.json")
    html = subprocess.run(["curl", "-s", "https://leekwars.com/"], capture_output=True, text=True).stdout
    i = html.find("var __DATA__=")
    if i >= 0:
        data, _ = json.JSONDecoder().raw_decode(html[i + len("var __DATA__="):])
        os.makedirs(lw.CACHE, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data["data"], f)
        return data["data"]
    with open(path) as f:  # repli : dernière copie
        return json.load(f)


def main():
    g = game_data()
    items, schemes, comps = g["items"], g["schemes"], g["components"]
    farmer = lw.get("farmer/get-from-token")["farmer"]
    stock = {}
    for kind in ("resources", "components", "chips", "weapons", "potions"):
        for r in farmer.get(kind) or []:
            stock[r["template"]] = stock.get(r["template"], 0) + r["quantity"]
    owned = {int(items[str(s["template"])]["params"]) for s in farmer["schemes"]}
    by_result = {s["result"]: s for s in schemes.values()}
    name = lambda t: items.get(str(t), {}).get("name", str(t))  # noqa: E731
    by_name = {c["name"]: c for c in comps.values()}

    def missing(item, qty, st, depth=0):
        have = st.get(item, 0)
        use = min(have, qty)
        st[item] = have - use
        qty -= use
        if qty == 0:
            return []
        sc = by_result.get(item)
        if sc and sc["id"] in owned and depth < 6:
            out = []
            for _ in range(qty):
                for ing in sc["items"]:
                    if ing:
                        out += missing(ing[0], ing[1], st, depth + 1)
            return out
        return [(item, qty)]

    ready, close = [], []
    print("COMPOSANTS UTILES")
    for n in TARGETS:
        c = by_name.get(n)
        if not c:
            continue
        sc = by_result.get(c["template"])
        stats = ", ".join(f"{k} {v:+d}" for k, v in c["stats"])
        if not sc or sc["id"] not in owned:
            print(f"  {n:15} ({stats}) : plan non possédé")
            continue
        agg = {}
        for it, q in missing(c["template"], 1, dict(stock)):
            agg[name(it)] = agg.get(name(it), 0) + q
        if not agg:
            ready.append(n)
            print(f"  {n:15} ({stats}) : FABRICABLE")
        else:
            if sum(agg.values()) <= 2:
                close.append(n)
            print(f"  {n:15} ({stats}) : manque " + ", ".join(f"{k} x{v}" for k, v in agg.items()))
    ids = {v["name"]: v["id"] for v in items.values()}
    print("STOCK : " + ", ".join(f"{r} {stock.get(ids.get(r), 0)}" for r in KEY_RESOURCES))
    print("RÉSUMÉ : fabricables =", ready or "aucun", "| presque (≤ 2 ressources manquantes) =", close or "aucun")


if __name__ == "__main__":
    main()
