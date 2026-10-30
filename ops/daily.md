# Tâche quotidienne de préparation (mode opératoire)

> Exécutée chaque jour par une tâche planifiée Claude, sur `main`. Tout se fait depuis la racine du dépôt.
> Règles de fond : `strategy/brand.md`, `strategy/playbook.md`, `config/accounts/eliott.elite.yaml`.

## 0. Préparer
```bash
git checkout main && git pull --rebase origin main
pip install -q -r requirements.txt
python3 scripts/check_env.py
```
Si un contrôle est KO : s'arrêter et le dire dans le résumé.

## 1. Synchroniser l'inbox
```bash
python3 scripts/sync_inbox.py download    # nouveaux fichiers -> data/library.json (description vide)
python3 scripts/sync_inbox.py previews    # planches dans work/previews/
```
- **Regarder chaque planche** (Read) et décrire chaque nouveau média dans `data/library.json` → `description` :
  `place, mood, category (lifestyle|sport), quality (1-5), tags[], summary, ideas` ; `usable` = qualité ≥ 2.
- Vidéos : `meta.audio.speech` (`yes|maybe|no`, Silero VAD) est un indice ; confirmer en regardant les images
  pendant `speech_segments` (personne face caméra, bouche qui bouge). Noter qui parle si visible.
- Signaler dans `description.warning` tout ce qui ne doit pas être montré : pièce d'identité, plaque lisible
  de tiers, écran avec données perso, tiers en gros plan, texte incrusté (stickers Instagram), armes.
- Puis : `python3 scripts/sync_inbox.py archive` (déplace vers `Insta/archive` les fichiers décrits).

## 2. Calendrier
```bash
python3 scripts/plan_calendar.py          # complète les 14 jours, vérifie les règles (exit 1 si violation)
```
Ajuster à la main si le playbook le demande (ex. décaler un Reel faute de vidéo). Ne jamais toucher un
créneau `proposed`/`queued`/`published`.

## 3. Proposer (créneaux des 48 prochaines heures, statut `planned`)
Pour chaque post/Reel, et pour chaque jour de stories :
1. Choisir les médias (`usable`, sans `warning` bloquant, règles de réutilisation : 2 fois max, ≥ 60 jours,
   format différent — vérifié automatiquement). Carrousel : même lieu ou même ambiance, la plus forte en
   couverture, sport jamais en premier, 1 image sport max.
2. Faire un rendu d'essai et **le regarder** (cadrage, horizon, tiers, données perso). Corriger `focus`,
   `zoom`, `rotate`, `start`/`duration`.
3. Écrire `work/proposals/<groupe>.json` (format en tête de `scripts/propose.py`) : légende (0-6 mots,
   anglais), `musique` (Reels → true sauf voix ; posts → false sauf ambiance qui s'y prête), 2-3 sons
   Instagram justifiés si `musique: true`, `voix`, `why`.
4. ```bash
   python3 scripts/propose.py render work/proposals/<groupe>.json
   python3 scripts/propose.py ship <groupe>
   ```
5. Attendre que le déploiement « pages build and deployment » du commit soit `success` (outil GitHub
   `actions_list`), puis ouvrir la PR (`create_pull_request`, base `main`, head `prop/<groupe>`, titre
   `work/proposals/<groupe>/title.txt`, corps `pr.md`).
6. `python3 scripts/propose.py mark <groupe> <numéro PR>`

## 4. Rattrapage
- PR encore ouverte alors que l'heure limite (2 h avant) est passée : la fermer avec un commentaire, remettre
  le créneau en `planned` à une autre date (ou le supprimer), annuler l'usage dans `library.json`.
- `queue/late/` et `queue/failed/` : reprogrammer ou abandonner, retirer le fichier, le dire dans le résumé.
- `published/` : passer les `uses` correspondants à `status: published`, créneau → `published`.

## 5. Résumé (message final de la tâche)
Court, en français : PR ouvertes (liens), publications d'hier, problèmes. **Si le stock ne tient pas la
semaine suivante** (moins de ~10 photos `usable` non utilisées de qualité ≥ 4, ou moins de 3 vidéos ≥ 7 s
pour les Reels) : **liste de tournage** précise (quoi, où, cadrage, durée).
