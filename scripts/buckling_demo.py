#!/usr/bin/env python3
"""buckling_demo.py — démo sandbox buckling-beam (concept Bi-FORK).

Bi-FORK (arXiv:2610.12449, code ml-jku/Bi-FORK) traite les bifurcations
1-entrée -> N-solutions. Ici on montre le phénomène physique sous-jacent
sans le modèle lourd : flambage d'Euler, bifurcation fourche (pitchfork).

Modèle : barre rigide + ressort de torsion k, charge axiale P.
Équilibre : P*L*sin(t) = k*t  soit  λ*sin(t) - t = 0, λ = P*L/k.
  λ < 1 : seule solution t = 0 (droite).
  λ > 1 : t = 0 instable + 2 branches symétriques ±t (flambe à gauche/droite).

Le point clé pour le ML : un surrogate déterministe prédit la MOYENNE (≈0),
donc une poutre droite sous charge supercritique — physiquement faux.
Bi-FORK génère les 2 branches (repulsion-guided sampling).

Usage:
    python scripts/buckling_demo.py --out outputs/buckling
"""

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    from scipy.optimize import brentq
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def branch_angle(lam: float) -> float:
    """Angle de la branche non-triviale pour λ > 1, sinon 0."""
    if lam <= 1.0:
        return 0.0
    f = lambda t: lam * np.sin(t) - t
    if HAS_SCIPY:
        return float(brentq(f, 1e-9, np.pi - 1e-6))
    # bissection de secours
    lo, hi = 1e-9, np.pi - 1e-6
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return float(0.5 * (lo + hi))


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagramme de bifurcation du flambage")
    ap.add_argument("--out", default="outputs/buckling")
    ap.add_argument("--lmax", type=float, default=3.0)
    ap.add_argument("--n", type=int, default=120)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lams = np.linspace(0.2, args.lmax, args.n)
    amps = np.array([branch_angle(l) for l in lams])

    # Stats démo "mode collapse"
    lam_demo = 2.0
    a_demo = branch_angle(lam_demo)
    deterministic_mean = 0.0  # moyenne des 2 branches = prédiction du surrogate naïf
    branch_gap = 2 * a_demo
    print(f"Charge lam={lam_demo} (lamc=1.0) : branches +-{a_demo:.3f} rad, ecart {branch_gap:.3f}")
    print(f"Surrogate deterministe -> moyenne {deterministic_mean:.3f} = poutre droite (FAUX, instable)")
    print("Branches distinctes recuperees : 2/2 (Bi-FORK vise exactement ca)")

    np.savetxt(out / "bifurcation.csv", np.column_stack([lams, amps]),
               delimiter=",", header="lambda,theta_branch", comments="")

    if HAS_MPL:
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))

        ax[0].plot(lams, amps, "b-", lw=2, label="branche +")
        ax[0].plot(lams, -amps, "r-", lw=2, label="branche −")
        ax[0].plot(lams, np.zeros_like(lams), "k--", lw=1, label="droite (instable si λ>1)")
        ax[0].axvline(1.0, color="gray", ls=":", label="λc = 1 (Euler)")
        ax[0].set_xlabel("charge normalisée λ = PL/k")
        ax[0].set_ylabel("angle θ (rad)")
        ax[0].set_title("Fourche de bifurcation (pitchfork)")
        ax[0].legend(fontsize=8)
        ax[0].grid(alpha=0.3)

        x = np.linspace(0, 1, 200)
        for sign, color in ((1, "blue"), (-1, "red")):
            w = sign * a_demo * 0.35 * np.sin(np.pi * x)  # mode 1, amplitude illustrative
            ax[1].plot(x, w, color=color, lw=2, label=f"branche {'+' if sign > 0 else '−'}")
        ax[1].plot(x, np.zeros_like(x), "k--", lw=1, label="moyenne = 0 (faux)")
        ax[1].set_xlabel("x / L")
        ax[1].set_ylabel("flèche w")
        ax[1].set_title(f"2 solutions valides pour UNE charge λ={lam_demo}")
        ax[1].legend(fontsize=8)
        ax[1].grid(alpha=0.3)

        fig.tight_layout()
        fig.savefig(out / "buckling.png", dpi=110)
        print(f"OK {out / 'buckling.png'} + bifurcation.csv")
    else:
        print("(matplotlib absent : CSV seul, pas de PNG)")
        print(f"OK {out / 'bifurcation.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
