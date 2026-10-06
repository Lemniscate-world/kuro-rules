# PRD — Programme B etape 2 : double-coeur avec secours (PRIVE, non commite)

## Problem Statement
Si le PC s eteint, Kuro perd son cerveau (Ollama local) ET sa memoire
(63 projets / 66 alertes dans `~/.kuro/kuro.db`) : le serveur, censé
secourir, est vide (0 projet) et aveugle.

## Target User
L operateur (1 personne) qui veut : voir l etat complet depuis le serveur
meme PC eteint, et promovoir le serveur en < 5 min quand il le decide.

## Solution
Standby chaud PASSIF sur le serveur : le PC pousse un snapshot coherent
de sa DB (API backup SQLite, jamais de cp brut sur base ouverte) toutes
les 5 min ; le serveur l expose en lecture seule ; la promotion est
MANUELLE (1 commande : backup du live, installation du replica, restart,
annonce). Jamais de promotion auto (PC eteint la nuit = normal),
jamais 2 ecrivains (anti split-brain par construction).

## User Stories
1. PC eteint le soir : `xenon` (ex `kuro-glances`) sur le serveur montre quand meme
   les 63 projets et les alertes (replica vieux de < 10 min).
2. PC mort un matin : 1 commande promeut le serveur (DB live = replica,
   daemon relance, endpoints 200), sans perte au-dela du RPO.
3. PC de retour : procedure inverse documentee, aucun merge magique,
   retour au nominal sans divergence silencieuse.

## Non-goals
Promotion automatique ; multi-writer temps reel ; transport Helium ;
entrainement/finetuning ; facturation ; chiffrement du replica au repos
(documente comme risque accepte : reseau prive + SSH).

## Success Metrics
- RPO <= 10 min (push 5 min + marge) ; promotion < 5 min chrono.
- 0 split-brain (aucune ecriture concurrente constatee).
- TUI/API lisent le replica sans erreur quand le primaire est jointable
  ou non (meme code, meme format).
- Suite verte des 2 cotes + bascule prouvee de bout en bout (test reel).

## Out of scope pour MVP
Petit modele LLM sur serveur ; alerting Discord/WhatsApp du dead-man ;
 Litestream temps reel (si RPO 5 min insuffisant, revoir) ; page plein
 ecran ; multi-coeurs (>2).
