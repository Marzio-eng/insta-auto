# eliott.elite — identité de marque

> Document de référence pour toute production (choix des médias, montage, légendes).
> Le playbook (`strategy/playbook.md`) peut affiner ces règles chaque semaine, jamais les contredire sans validation d'Eliott.

## 1. Positionnement

**On ne prouve pas, on montre.** Un train de vie classe, du luxe discret, une vie perso montrée avec élégance. Nonchalance maîtrisée — « aura farming ».

| Part | Thèmes |
|---|---|
| **≥ 80 % lifestyle / branding** | voyages, hôtels, restaurants, voitures, soirées, couchers de soleil, architecture, piscines, vie perso élégante |
| **≤ 20 % sport, en discret** | boxe, MMA, grappling, JJB, muscu, boxe chinoise — toujours intégré à l'esthétique « train de vie », jamais un compte de sport |

**Dosage sport (modèle keo.snb)** : le sport apparaît comme *une image au milieu d'un carrousel lifestyle* (sac de frappe torse nu, salle avec vue sur la ville), ou en story. Pas de post 100 % sport, pas de tuto, pas de chiffres de perf en légende.

## 2. Ton et légendes

- Langue : **anglais**.
- Sérieux mais chill, nonchalant. Jamais d'explication, jamais d'appel à l'action (« like », « follow », « link in bio » : interdits).
- **0 à 6 mots**, souvent en minuscules, ponctuation minimale.
- Emojis rares et choisis : drapeau du pays, ✨, 🌙, 🖤 — un ou deux au plus, souvent seuls.
- Hashtags : 0 à 3, seulement s'ils servent vraiment (souvent aucun).
- Localisation renseignée quand c'est possible (lieu réel, pas d'invention).

Bons exemples : `Bruce wayne life` · `✨🇮🇹` · `quiet.` · `another one` · `late checkout` · `same city, new view` · `🌙`

À éviter : phrases motivationnelles, « grind », « blessed », listes d'emojis, questions au public, hashtags génériques (#luxury #lifestyle #motivation).

## 3. Références de style

### keo.snb — référence principale pour les posts
- Très peu de posts (25), **tous en carrousels de vie**.
- Ambiance **nuit / sombre** : supercars, architecture moderne éclairée, piscine à débordement, repas, sac de frappe torse nu avec vue sur la ville.
- Légendes ultra courtes (« Bruce wayne life »). Bio minimaliste.
- Highlights : « Stats », « Life 5 », « Life 6 »…
- Le sport = une image dans un carrousel lifestyle → **dosage exact voulu**.
- *Constat API (Business Discovery, 29/10/2026)* : ses publications récentes renvoyées par l'API sont des **Reels** (série « Le secret de ma réussite… », souvent en double, likes très variables : 1 → 19 000) qui n'apparaissent pas sur la grille — vraisemblablement des Reels d'essai / sponsorisés. La grille reste la référence esthétique ; les Reels sont un canal d'acquisition séparé.

### yomidenzel
- Photos de qualité pro : tapis rouge, hélicoptère, Dubaï, St-Tropez, Cannes.
- Highlights classés **par lieu**.
- Reels = extraits de podcast avec **accroche en gros texte blanc encadré en haut** + un emoji.

### marvinndiaye_
- Images **cinématiques, sombres, tons chauds**, portraits pensifs.
- Carrousels « storytelling » avec texte superposé (mots clés en couleur).
- Highlights à **couvertures uniformes**.

### keo0
- Reels face caméra, format « réponse à un commentaire », captures de stats.
- **Accroche forte dans la première seconde.**

### Ce qu'on prend / ce qu'on laisse
| On prend | On laisse |
|---|---|
| Carrousels de vie, ambiance nuit (keo.snb) | Le discours business / coaching (marvinndiaye_, keo0) |
| Qualité photo pro, classement par lieu (yomidenzel) | Les Reels podcast parlés (pas notre format pour l'instant) |
| Étalonnage chaud et sombre (marvinndiaye_) | Le texte storytelling lourd sur les posts |
| Accroche visuelle à la 1re seconde des Reels (keo0) | Les appels à commenter |

## 4. Le compte aujourd'hui (eliott.elite)

- 4 publications, toutes en carrousels : BMW de nuit avec éclairage de seuil, tours la nuit au bord de l'eau, stade d'Arsenal, villa en Toscane au coucher du soleil, cocktails, restaurants, gnocchis + vin blanc, piscine.
- Légendes minimalistes (« ✨🇮🇹 »), localisation renseignée.
- Highlights : Life, Highlights, Stats, Daily Fun, Lifestyle.
- **Point faible** : photos de téléphone parfois sous-exposées ou sans retouche cohérente → corrigé par l'étalonnage maison ci-dessous.

## 5. Règles visuelles (tout le contenu)

### Étalonnage maison « Elite Warm »
Objectif : cohérence de grille, **aucun filtre visible**.
- **Tons chauds** : légère dérive vers l'ambre dans les hautes lumières et les tons moyens (balance des blancs +200 à +400 K environ).
- **Noirs profonds mais pas bouchés** : point noir légèrement relevé (les noirs ne descendent pas à 0), détail conservé dans les ombres.
- **Ombres légèrement relevées**, hautes lumières protégées (pas de ciel cramé).
- **Saturation retenue** (≈ −10 à −15 %), peaux naturelles, pas de teal & orange appuyé.
- Photos sous-exposées : remontée d'exposition et des ombres *avant* l'étalonnage ; bruit atténué si nécessaire.
- Même traitement pour photos, stories et Reels (implémenté une seule fois dans `scripts/`, réglages versionnés).

### Cadrage
- **Horizon droit** (correction automatique ± quelques degrés, vérifiée à l'œil).
- Recadrage propre au format cible, sujet centré ou sur les tiers, pas de bandes noires.
- Posts : **1080×1350 (4:5)** JPEG. Stories / Reels : **1080×1920 (9:16)**.
- Carrousels : jusqu'à 10 images **cohérentes** (même lieu ou même ambiance), la plus forte en première, une image « respiration » (détail, texture) au milieu, le sport éventuel jamais en premier.

### Texte sur image (rare)
- Police sobre sans empattement, blanc cassé, petite taille, une ligne courte.
- Autorisé : story stats/texte sobre, ligne discrète sur un Reel. Pas de texte sur les posts de grille.

## 6. Formats et rythme (rappel — détail dans `config/accounts/eliott.elite.yaml`)

- Stories : 2-3 / jour, 10h-23h30, ≥ 2 h d'écart.
- Posts : 3-5 / semaine. Reels : 3 / semaine. Fenêtre 17h-22h, jamais à heure ronde, ≤ 1 post ou Reel par jour.
- Réutilisation d'un média : 2 fois max, ≥ 60 jours d'écart, format différent.

## 7. Musique — vraie musique Instagram, mode semi-automatique

L'API Instagram ne permet pas d'ajouter un son de la bibliothèque Instagram. Or on veut le **vrai son Instagram** (titre visible sur la publication). Donc :

- **Aucune musique n'est jamais intégrée dans les fichiers**, et aucune musique protégée n'est utilisée.
- Chaque publication a un champ `"musique"` :
  - `false` → publiée automatiquement par l'API ;
  - `true` → **semi-automatique** : tout est préparé (montage, recadrage, étalonnage, légende), mais c'est Eliott qui publie depuis l'appli Instagram en choisissant le son.

### Répartition
| Format | Règle |
|---|---|
| **Reels** | toujours `true` (sauf Reel où Eliott parle, voir plus bas) |
| **Stories** | **≥ 70 % `true`**, ≤ 30 % `false` — vérifié sur chaque **semaine glissante** dans `data/calendar.json`. Les `false` sont les stories où la musique n'a pas sa place : texte / stats, info pratique, vidéo parlée. |
| **Posts / carrousels** | `false` par défaut, `true` seulement quand le post s'y prête vraiment (ambiance, voyage, soirée, sport…) |

### Vidéos où Eliott parle
- Détection de la voix : analyse audio ffmpeg (niveaux, bande de fréquences de la parole, `silencedetect`) **et** vérification en regardant/écoutant quelques extraits.
- Le son d'origine est **toujours conservé**, la voix parfaitement audible ; **on ne coupe jamais une phrase** au montage.
- Par défaut **pas de musique** (`false`) : ces stories comptent dans les 30 % sans musique ; les Reels parlés sont l'exception à « Reels → toujours `true` ».
- Si une ambiance discrète apporte vraiment quelque chose : `true`, et la page de partage indique de **baisser la musique à ~10-20 %** dans Instagram, son d'origine à 100 %.

### Choix des sons
- Le son **colle au contexte précis** : lieu, moment, ambiance, action, rythme de la vidéo.
  - coucher de soleil en Toscane → italien ou chill ;
  - sac de frappe la nuit → sombre et rythmé ;
  - voiture de nuit → lent et grave.
- Jamais un son choisi *uniquement* parce qu'il est tendance.
- Pour chaque publication `true` : **2 ou 3 sons Instagram** (titre exact + artiste), chacun avec **une phrase de justification** et le passage à utiliser si utile.

### Page de partage
Pour chaque publication `true`, une page `docs/share/<id>.html` (servie par GitHub Pages, pensée pour le téléphone) :
aperçu du média · gros bouton **« Ouvrir dans Instagram »** (API Web Share : le fichier arrive directement dans l'éditeur Instagram, et la légende est copiée au même clic) · bouton « Copier la légende » de secours · sons conseillés · format à choisir (Story / Reel / Publication) · bouton « Télécharger le fichier » si le partage n'est pas pris en charge.
