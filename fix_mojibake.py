import os

targets = [
r"C:\Users\Utilisateur\Documents\kuro-rules\AGENTS.md",
r"C:\Users\Utilisateur\Documents\AEther\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Automatons\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Kapok\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Iroko\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Verbose\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Vault\AGENTS.md",
r"C:\Users\Utilisateur\Documents\TokenWise\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Helium\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Astral\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Charmed\AGENTS.md",
r"C:\Users\Utilisateur\Documents\CADAM\AGENTS.md",
r"C:\Users\Utilisateur\Documents\OpenQuant\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Sagittarius\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Project-Dirac\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Playground\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Echo\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Dissect\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Datalint\AGENTS.md",
r"C:\Users\Utilisateur\Documents\BloomDB\AGENTS.md",
r"C:\Users\Utilisateur\Documents\NeuroDose\AGENTS.md",
r"C:\Users\Utilisateur\Documents\NeuralPaper\AGENTS.md",
r"C:\Users\Utilisateur\Documents\NeuralDSL\AGENTS.md",
r"C:\Users\Utilisateur\Documents\OpenMind\AGENTS.md",
r"C:\Users\Utilisateur\Documents\NeuralDBG\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Lemniscate-world\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Neural-Research\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Neural-Aquarium\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Neural-Again\AGENTS.md",
r"C:\Users\Utilisateur\Documents\Metatron\AGENTS.md"
]

replacements = {
    "ÔÇô": "—",
    "├âÔÇö": "×",
    "Ã©": "é",
    "Ã¨": "è",
    "Ã": "à"
}

for target in targets:
    if os.path.exists(target):
        try:
            with open(target, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(target, 'r', encoding='cp1252') as f:
                content = f.read()
                
        for k, v in replacements.items():
            content = content.replace(k, v)
            
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
print("Mojibakes cleaned up successfully in all repos.")
