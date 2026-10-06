# Dépôt apt privé Kuro — guide de publication (humain requis)

Le `.deb` se construit sans sudo (`packaging/deb/build-deb.sh`, testé sur
Ubuntu 24.04). Reste côté humain :

## Option A — install directe (test, 1 machine)

```bash
sudo dpkg -i kuro_1.3.0-1_all.deb
sudo apt-get install -f   # répare les Depends si besoin
```

## Option B — mini dépôt apt signé (recommandé, `apt install kuro`)

Sur le serveur, une fois (nécessite sudo + une clé GPG) :

```bash
# 1. Clé de signature (TODO : générer, `gpg --full-generate-key`)
# 2. Dépôt reprepro
sudo apt-get install -y reprepro
mkdir -p /var/www/apt/{conf,dists,pool}
# conf/distributions : Origin: lambda-Section / Suite: stable / Architectures: all ...
reprepro -b /var/www/apt includedeb stable kuro_1.3.0-1_all.deb
# 3. Servir /var/www/apt en HTTP local (Caddy/nginx) + publier la clé publique
```

Côté client :

```bash
curl -fsSL http://<serveur>/kuro-apt.gpg | sudo gpg --dearmor -o /usr/share/keyrings/kuro.gpg
echo "deb [signed-by=/usr/share/keyrings/kuro.gpg] http://<serveur>/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/kuro.list
sudo apt-get update && sudo apt-get install kuro
```

## Option C — GitHub Release (simple, sans dépôt)

Attacher le `.deb` à la release GitHub `v1.3.0-kuro`, puis :

```bash
wget https://github.com/Lemniscate-world/kuro-rules/releases/download/v1.3.0-kuro/kuro_1.3.0-1_all.deb
sudo dpkg -i kuro_1.3.0-1_all.deb
```

Pas de PPA officiel : trop lourd pour ce stade (R8 : plus simple d'abord).
