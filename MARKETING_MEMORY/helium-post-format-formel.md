# Helium - Format Post Formel (préférence utilisateur 2026-09-20)

## Langue et ton
- Français formel uniquement, vouvoiement.
- Ne pas utiliser : "pote", "dort", "blinde", slang TikTok.
- Ton : factuel, professionnel, accessible non-expert.
- Phrases courtes.

## Structure obligatoire pour tout post Helium
1. **Helium : présentation** (3 lignes max)
   - Définition : réseau privé de partage de ressources de calcul (GPU/RAM) pour l'IA.
   - Section : fait partie de Helium Communities = groupes fermés de membres de confiance, pas marketplace public anonyme.
   - Objectif : utiliser le matériel existant sous-exploité, alternative au cloud centralisé.
2. **Travaux réalisés aujourd'hui** (liste numérotée, factuelle)
   - Version + composant (ex : helium-mesh v0.1).
   - Livrables concrets, sans hype, sans promesse de date future.
3. **Prochaine étape** (1 phrase).
4. **Caption** courte pour copier-coller.

## Intelligence attendue les prochaines fois
Quand l'utilisateur demande "aide pour un post" / "post helium" / "post du jour" :
1. Vérifier automatiquement ce qui a été fait aujourd'hui : `git log --oneline -5`, `git status --short`, fichiers modifiés du jour dans `helium-mesh/`, `install.sh`, `helium/`.
2. Rappeler la définition Helium + section Communities sans redemander.
3. Proposer directement le post au format ci-dessus, en formel.
4. Ne pas demander les photos Glances, juste laisser un placeholder [X GB RAM, X% idle] si pertinent.
5. Ne pas proposer de version familière sauf demande explicite.

## Exemple validé
Helium est un réseau privé de partage de ressources de calcul, principalement GPU et RAM, destiné aux projets d'intelligence artificielle.
Il s'inscrit dans Helium Communities, c'est-à-dire des groupes fermés composés de membres de confiance, par opposition à une place de marché publique et anonyme.
L'objectif est d'utiliser le matériel existant, souvent sous-exploité, comme alternative aux offres cloud centralisées et aux interruptions des environnements gratuits.

Travaux réalisés aujourd'hui :
1. Création du binaire principal avec les commandes d'initialisation de nœud, de gestion du réseau et d'affichage du statut.
2. Mise en place du système d'identité cryptographique et du mécanisme d'invitation avec expiration.
3. Développement du script d'installation automatisé, incluant la vérification de compatibilité de la machine hôte.
