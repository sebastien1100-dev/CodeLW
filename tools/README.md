# Outils Leek Wars

Scripts pour tester et piloter les IA du compte depuis un environnement où le proxy injecte la
clé API Leek Wars (aucun secret dans le dépôt).

| Fichier | Rôle |
|---|---|
| `lw.py` | Accès API (limite 5 req/s, DELETE en JSON), noms des armes/puces, scénarios de test |
| `capital.py` | Barème du capital, conversion achats ↔ stats |
| `bench.py` | Bancs de test gratuits (scénarios) : duel, A/B, clones de répartition, 4 contre 4 |
| `fights.py` | Lancement des **vrais** combats du jour et bilan (consomme les combats) |
| `kits.json` | Équipements à tester (`--kit`) |
| `builds.json` | Répartitions de capital à tester (`--build`) |

## Tester un changement d'IA

```bash
python3 tools/bench.py upload ais/Opti.leek --as OptiDev
```

```bash
python3 tools/bench.py ab --hero Kador --ai Opti --ai2 OptiDev --opps sebo,jessy,Enzo --seeds 8
```

```bash
python3 tools/bench.py team --ai OptiDev --seeds 6
```

Si `OptiDev` gagne nettement (au moins ~10 points, confirmé sur une 2e série avec `--seed0 20`),
on l'envoie sous le nom `Opti`, utilisé par les 4 poireaux :

```bash
python3 tools/bench.py upload ais/Opti.leek --as Opti
```

## Ce qu'on peut et ne peut pas tester

- Les scénarios sont **gratuits et illimités** ; les défis du potager sont limités par jour.
- On peut changer l'IA et l'équipement (`--kit`) d'un vrai poireau, y compris avec des objets non possédés.
- Les stats d'un vrai poireau ne peuvent pas être modifiées : `--build` crée un **clone** (mêmes armes,
  puces et bonus de composants, stats recalculées depuis le capital).
- On ne peut pas affronter les poireaux d'autres joueurs, seulement les nôtres et les bots
  (`domingo, betalpha, tisma, guj, hachess, rex`, IA `@expert`).
- Un kit doit garder les composants de récupération (cœurs/RAM), sinon l'IA tombe à 1 cœur et plante
  faute d'opérations ; `bench.py` les reprend automatiquement.
- Composants : chaque composant de récupération (406, 407) bloque 2 emplacements ; avec les deux,
  seuls les 4 premiers emplacements comptent.

## Bruit statistique

Chaque graine est jouée des deux côtés. Sur 48 combats, l'écart-type d'un taux de victoire est
d'environ 7 points : ne conclure qu'au-delà de ~10 points, et le confirmer sur d'autres graines.
