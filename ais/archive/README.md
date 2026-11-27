# Archives

`OptiDev_boss_roi_fenouil.leek` : version d'Opti écrite par une autre session (27/11), récupérée de l'éditeur
Leek Wars avant suppression. Elle contient une stratégie pour le boss Roi Fenouil (fonctions `bossTurn`,
`moveCrystals`, `goalCells`…) :

- le Graal rend tous les ennemis invincibles (état `STATE_INVINCIBLE`) ;
- il s'autodétruit si chaque cristal projette son rayon sur lui (rouge vers y-1, vert vers y+1, bleu vers x-1,
  jaune vers x+1) ;
- on déplace les cristaux en ligne droite avec le Gant de boxe (pousse), le Grappin (attire) ou l'Inversion
  (échange) ;
- **ne jamais tuer un cristal tant que le Graal vit** : cela déclenche l'Apocalypse, qui tue toute l'équipe.

Cette stratégie n'a pas été testée ici : elle demande des puces que nos poireaux n'ont pas.
