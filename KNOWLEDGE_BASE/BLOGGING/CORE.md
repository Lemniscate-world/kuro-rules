# BLOGGING — Socle condensé (R110)

## Avant d'écrire
1. Choisir le type : deep-dive / build log / tutorial / opinion / post-mortem
2. Lecteur cible spécifique : que sait-il, quel problème a-t-il maintenant ?
3. Tous les chiffres viennent du pipeline vérité (git, tests, Epingle). Zéro invention.

## Structure gagnante
- **Ouverture** = problème vécu ou conséquence. Jamais une définition.
- **TL;DR** (2-3 phrases) si > 800 mots
- **H2 riches et spécifiques**, code exécutable toutes les 3-5 paragraphes
- Problème → approches ratées → solution → gotchas → synthèse

## Style
- 2ᵉ personne, direct, zéro jargon-gatekeeping ("évidemment", "il suffit de")
- Claim sans source = interdit (lien officiel / benchmark / nos mesures git)
- Édition : passe suppression, passe précision, lecture à voix haute

## Ne jamais publier
Données clients · détails de sécurité exploitables · roadmap avec timelines ·
drama · posts émotionnels · données financières au-delà du volontairement public

## Distribution (après publication canonique auto-hébergée)
X thread 5 tweets → HN (mar/jeu matin US) → Reddit (culture du sub lue avant) →
LinkedIn (angle décisions) → Discord communautés dont la nôtre.
Syndication dev.to/Hashnode/Medium AVEC `rel=canonical` vers l'original.

## Checklist express (12 points)
Titre cherchable · pourquoi clair · sommaire si long · pourquoi→quoi→comment ·
diagrammes · code qui tourne · alternatives discutées · chiffres mesurés ·
takeaways · sources liées · orthographe/liens · meta+OG

Sources complètes : `rules/rule_110_blogging.md` § R110.8
