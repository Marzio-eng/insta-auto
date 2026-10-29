# insta-auto

Gestion automatisée du compte Instagram **eliott.elite**, entièrement dans le cloud.

| Étape | Où | Quand |
|---|---|---|
| Dépôt des médias bruts | Google Drive `Insta/inbox` (+ `musique`, `archive`) | quand Eliott veut |
| Préparation (tri, montage, planning, PR) | tâche planifiée Claude | 1×/jour |
| Validation | bouton **Merge** de la PR | Eliott, depuis l'appli GitHub |
| Publication | GitHub Action `publish` | toutes les 15 min |
| Apprentissage (stats, playbook) | tâche planifiée Claude | 1×/semaine |

## Arborescence
```
config/accounts/<compte>.yaml   réglages par compte (multi-comptes prêt)
strategy/brand.md               identité, ton, règles visuelles
strategy/playbook.md            ce qui marche (mis à jour chaque semaine)
data/library.json               médias connus + description + historique d'usage
data/calendar.json              planning des 14 prochains jours
data/stats/                     statistiques par publication
docs/media/                     fichiers servis par GitHub Pages (JPEG / MP4)
queue/                          publications validées (1 JSON chacune)
published/                      historique publié (avec l'ID Instagram)
scripts/                        code Python (requests, cryptography, pyyaml)
.github/workflows/              publication, vérification du jeton
```

## Secrets
Jamais dans le dépôt (public). Secrets GitHub : `IG_TOKEN`, `IG_USER_ID`.
Environnement Claude : `GDRIVE_SA_JSON`, `GDRIVE_FOLDER_ID`, `IG_TOKEN`, `IG_USER_ID`.

## Vérifier l'environnement
```bash
pip install -r requirements.txt
python3 scripts/check_env.py
```
