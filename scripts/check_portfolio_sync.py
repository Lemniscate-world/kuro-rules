#!/usr/bin/env python3
"""Pre-commit hook: warn if Epingle_Projets.md changed but portfolio not regenerated.

Place this in .git/hooks/pre-commit or run via pre-commit config.
"""

import subprocess, sys
from pathlib import Path

def main():
    # Check if Epingle_Projets.md is staged
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True
    )
    staged = result.stdout.splitlines()
    
    if "Epingle_Projets.md" not in staged:
        return 0  # not modified, nothing to do
    
    # Epingle was modified — regenerate portfolio
    print("\n⚠️  Epingle_Projets.md modified. Regenerating portfolio...")
    
    gen_script = Path(__file__).resolve().parent.parent / "scripts" / "generate_portfolio.py"
    result = subprocess.run(
        ["python", str(gen_script)],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Portfolio generation failed:\n{result.stderr}")
        return 1
    
    print(result.stdout)
    
    # Check if the generated HTML has changes
    lemniscate = Path.home() / "Documents" / "Lemniscate-world"
    result = subprocess.run(
        ["git", "-C", str(lemniscate), "diff", "--quiet", "index.html"],
        capture_output=True
    )
    
    if result.returncode != 0:
        print("⚠️  Portfolio HTML has uncommitted changes in Lemniscate-world.")
        print("   Run: cd ~/Documents/Lemniscate-world && git add index.html && git commit -m 'sync portfolio' && git push")
        print("   Or the GitHub Action will sync it automatically on push.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
