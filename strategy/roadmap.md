# Feuille de route

## Phase 1 — fondations ✅
Environnement, Drive, API Instagram, Business Discovery (4/4), structure du dépôt, GitHub Pages, conteneur de test accepté sans publication.

## Phase 2 — posts et stories de bout en bout (avec mode semi-automatique)

### Format d'une publication en file d'attente (`queue/<date>_<type>_<id>.json`)
```json
{
  "id": "20261103-post-tuscany",
  "type": "post | carousel | story | reel",
  "scheduled_at": "2026-11-03T19:47:00+01:00",
  "caption": "✨🇮🇹",
  "media": [{"url": "https://marzio-eng.github.io/insta-auto/media/…jpg", "kind": "image"}],
  "musique": false,
  "sons_conseilles": [{"titre": "…", "artiste": "…", "pourquoi": "…", "passage": "0:42"}],
  "voix": false,
  "share_page": "https://marzio-eng.github.io/insta-auto/share/<id>.html",
  "library_ids": ["…"],
  "why": "…"
}
```

### Tâche de préparation (Claude, 1×/jour)
1. Synchronisation de `Insta/inbox` → analyse (images regardées, images clés extraites des vidéos, **détection de voix** avec ffmpeg et écoute d'extraits) → `data/library.json` → déplacement vers `Insta/archive`.
2. Calendrier de 14 jours (`data/calendar.json`) selon le rythme, avec le champ `musique` pour chaque créneau et le **contrôle du ratio stories ≥ 70 % avec musique sur chaque semaine glissante**.
3. Pour chaque publication à moins de 48 h : rendu avec l'étalonnage maison → `docs/media/` (commit direct sur `main`) ; si `musique: true`, page `docs/share/<id>.html` + 2-3 sons justifiés ; PR avec `queue/…json` (1 PR par post/Reel, 1 PR par jour de stories). La PR indique clairement « 🤖 auto » ou « 🎵 semi-auto (tu publies avec le son) ».
4. Une PR non mergée 2 h avant l'heure prévue → pas de publication, reprogrammation.
5. Rapprochement des publications semi-automatiques : retrouver via l'API (`/media`, `/stories`) la publication faite à la main, l'enregistrer dans `published/` avec son ID.

### GitHub Action `publish` (toutes les 15 min)
- `musique: false` → conteneur, attente `FINISHED`, publication, `queue/` → `published/` (avec l'ID), suppression des vidéos lourdes de `docs/media/`. Échec : 3 nouvelles tentatives, puis issue avec l'erreur exacte.
- `musique: true` → **pas d'appel de publication** : à l'heure prévue, ouverture d'une issue **assignée à Eliott** (notification sur le téléphone) avec le lien de la page de partage, les sons et la légende. Fichier déplacé dans `queue/pending_manual/`.
- Issue fermée → l'Action cherche la publication correspondante via l'API (même type, publiée après l'heure prévue, légende identique) et l'enregistre dans `published/`. **Important pour les stories** : l'API ne les expose que 24 h, donc ce rapprochement se fait dans l'Action (toutes les 15 min) et pas seulement dans la tâche quotidienne.
- Avant toute publication API : vérification que le déploiement GitHub Pages du commit qui contient le média a réussi.

### Premier test réel
Un premier post `musique: false` validé par PR et publié automatiquement, puis une story `musique: true` passée par la page de partage.

## Phase 3 — Reels et montage
Montage ffmpeg **sans musique intégrée** (coupes calées sur le rythme visuel ou sur le BPM du son conseillé, recadrage 9:16, étalonnage). Son d'origine conservé si Eliott parle. 2-3 versions d'un premier Reel, avec leurs sons conseillés.

## Phase 4 — apprentissage et robustesse
Stats (y compris celles des publications semi-automatiques), Business Discovery, playbook, vérification hebdomadaire du jeton (alerte 21 jours avant `data_access_expires_at`), parade aux 60 jours d'inactivité.

## Phase 5 — tâches planifiées Claude
Préparation quotidienne et analyse hebdomadaire, avec notifications.
