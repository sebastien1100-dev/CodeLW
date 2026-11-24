"""Accès à l'API Leek Wars (https://leekwars.com/api/) et utilitaires communs.

L'authentification est faite par le proxy de l'environnement (clé API injectée dans
l'en-tête Authorization) : aucun secret n'est stocké ici.
"""
import json
import os
import subprocess
import time

API = "https://leekwars.com/api/"
FARMER_ID = 14286
LEEKS = {"sebo": 15677, "jessy": 17004, "Enzo": 19177, "Kador": 24610}
BOTS = ("domingo", "betalpha", "tisma", "guj", "hachess", "rex")
CACHE = os.path.join(os.path.dirname(__file__), "cache")

_last_call = 0.0


def api(method, endpoint, **fields):
    """Appel API avec limitation de débit (5 req/s) et nouvelle tentative sur rate_limit.

    DELETE : paramètres en JSON (le serveur ignore les formulaires sur DELETE).
    Autres méthodes : paramètres en formulaire.
    """
    global _last_call
    for _ in range(5):
        wait = 0.22 - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        cmd = ["curl", "-s", "-X", method]
        if method == "DELETE":
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(fields)]
        else:
            for k, v in fields.items():
                cmd += ["--form-string", f"{k}={v}"]
        out = subprocess.run(cmd + [API + endpoint], capture_output=True, text=True).stdout
        try:
            res = json.loads(out)
        except ValueError:
            res = out
        if isinstance(res, dict) and res.get("error") == "rate_limit":
            time.sleep(res.get("retry_after", 1))
            continue
        return res
    return res


def get(endpoint):
    return api("GET", endpoint)


def _cached(name, endpoint, key=None):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        data = get(endpoint)
        with open(path, "w") as f:
            json.dump(data, f)
    with open(path) as f:
        data = json.load(f)
    return data[key] if key else data


def chips():
    """id de puce (= template côté éleveur/poireau, = constante CHIP_* en LeekScript) -> définition."""
    return _cached("chips.json", "chip/get-all", "chips")


def weapons():
    return _cached("weapons.json", "weapon/get-all", "weapons")


def chip_name(template):
    return chips()[str(template)]["name"]


def weapon_name(item):
    """Les armes sont référencées par leur numéro d'objet (champ 'item', = constante WEAPON_*)."""
    for w in weapons().values():
        if w["item"] == item:
            return w["name"]
    return str(item)


def leek(leek_id):
    r = get(f"leek/get-private/{leek_id}")
    return r.get("leek", r)


def loadout(leek_id):
    """Équipement actuel d'un vrai poireau, au format des scénarios de test."""
    l = leek(leek_id)
    return {
        "weapons": [weapon_name(w["template"]) for w in l["weapons"]],
        "chips": [chip_name(c["template"]) for c in l["chips"]],
        "components": [{"index": i, "template": c["template"]} for i, c in enumerate(l["components"]) if c],
    }


def upload_ai(path, code):
    """Écrit/compile un fichier d'IA ; renvoie la liste des problèmes de compilation."""
    r = api("POST", "ai/write", path=path, code=code)
    if isinstance(r, dict) and "result" in r:
        return r["result"].get(path, {}).get("problems", [])
    return r  # fichier JSON (scénario) : pas de compilation


def wait_fight(fight_id, tries=30):
    for _ in range(tries):
        r = get(f"fight/get/{fight_id}")
        r = r.get("fight", r) if isinstance(r, dict) else {}
        if r.get("status") == 2:
            return r
        time.sleep(2)
    return None


def ai_errors(fight_id):
    """Erreurs d'exécution de nos IA dans un combat : {"fichier, ligne #code": nombre}."""
    logs = get(f"fight/get-logs/{fight_id}")
    errs = {}
    if isinstance(logs, dict):
        for entries in logs.values():
            for lst in entries.values():
                for e in lst:
                    s = str(e[2])
                    if s.startswith("\t"):
                        k = s.split("\n")[0].strip() + " #" + str(e[3])
                        errs[k] = errs.get(k, 0) + 1
    return errs


def run_scenarios(scenarios, path="test_scenario.json"):
    """Lance des scénarios de test (illimités, gratuits) et renvoie [(id_combat, scénario)].

    Un fichier de scénario est un fichier JSON de l'éditeur d'IA ; on le réécrit avant chaque combat,
    donc ne pas lancer deux bancs en parallèle sur le même `path`.
    """
    out = []
    for sc in scenarios:
        upload_ai(path, json.dumps({k: v for k, v in sc.items() if not k.startswith("_")}))
        r = api("POST", "ai/test-scenario-file", path=path)
        if isinstance(r, dict) and "fight" in r:
            out.append((r["fight"], sc))
        else:
            print("échec du lancement :", r)
    return out
