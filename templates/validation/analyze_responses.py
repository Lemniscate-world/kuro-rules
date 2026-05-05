"""
Hermes Response Analyzer
Fetches validation responses from Supabase and generates insights.
Usage: python scripts/analyze_responses.py
"""

import os
import sys
from datetime import datetime
from collections import Counter

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# Config - set these or use env vars
SUPABASE_URL = os.environ.get("HERMES_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("HERMES_SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Set HERMES_SUPABASE_URL and HERMES_SUPABASE_KEY env vars")
    sys.exit(1)

LABELS = {
    "role": {"merchant": "Commercant", "driver": "Livreur", "both": "Les deux", "other": "Autre"},
    "business_type": {"restaurant": "Restaurant", "bakery": "Boulangerie", "pharmacy": "Pharmacie", "grocery": "Epicerie", "shop": "Boutique", "other": "Autre"},
    "volume": {"lt5_week": "<5/semaine", "5_20_week": "5-20/semaine", "1_5_day": "1-5/jour", "gt5_day": ">5/jour"},
    "main_problem": {"find_driver": "Trouver livreur", "coordination": "Coordination", "tracking": "Suivi", "proof": "Preuve", "other": "Autre"},
    "budget": {"free_only": "Gratuit", "5000_15000": "5-15K FCFA", "15000_30000": "15-30K FCFA", "30000_plus": ">30K FCFA"},
    "beta_interest": {"yes": "Oui", "maybe": "Peut-etre", "no": "Non"},
}


def fetch_responses():
    url = f"{SUPABASE_URL}/rest/v1/landing_responses?select=*&order=created_at.desc"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def analyze(data):
    total = len(data)
    if total == 0:
        print("Aucune reponse trouvee.")
        return

    qualified = [r for r in data if r.get("qualified")]
    beta_yes = [r for r in data if r.get("beta_interest") == "yes"]
    beta_maybe = [r for r in data if r.get("beta_interest") == "maybe"]
    willing = [r for r in data if r.get("willing_to_pay")]
    high_volume = [r for r in data if r.get("high_volume")]

    print_header("HERMES VALIDATION REPORT")
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Total responses: {total}")

    print_header("QUALIFICATION METRICS")
    print(f"  Commercants qualifies:     {len(qualified)} ({pct(len(qualified), total)})")
    print(f"  Volume eleve (>1/jour):     {len(high_volume)} ({pct(len(high_volume), total)})")
    print(f"  Interesses beta (oui):      {len(beta_yes)} ({pct(len(beta_yes), total)})")
    print(f"  Interesses beta (peut-etre):{len(beta_maybe)} ({pct(len(beta_maybe), total)})")
    print(f"  Volonte de payer:           {len(willing)} ({pct(len(willing), total)})")

    print_header("VALIDATION THRESHOLDS")
    print(f"  20+ reponses qualifiees:    {'PASS' if len(qualified) >= 20 else 'FAIL'} ({len(qualified)}/20)")
    print(f"  30%+ non-zero budget:       {'PASS' if total > 0 and len(willing)/total >= 0.3 else 'FAIL'} ({pct(len(willing), total)})")
    print(f"  5+ beta oui:                {'PASS' if len(beta_yes) >= 5 else 'FAIL'} ({len(beta_yes)}/5)")

    print_header("ROLE DISTRIBUTION")
    for value, count in Counter(r.get("role") for r in data).most_common():
        print(f"  {LABELS['role'].get(value, value):15s} {count:3d} ({pct(count, total)})")

    print_header("BUSINESS TYPE")
    for value, count in Counter(r.get("business_type") for r in data).most_common():
        print(f"  {LABELS['business_type'].get(value, value):15s} {count:3d} ({pct(count, total)})")

    print_header("PROBLEM DISTRIBUTION")
    for value, count in Counter(r.get("main_problem") for r in data).most_common():
        print(f"  {LABELS['main_problem'].get(value, value):15s} {count:3d} ({pct(count, total)})")

    print_header("BUDGET DISTRIBUTION")
    for value, count in Counter(r.get("budget") for r in data).most_common():
        print(f"  {LABELS['budget'].get(value, value):15s} {count:3d} ({pct(count, total)})")

    print_header("ZONES")
    for value, count in Counter(r.get("zone") for r in data if r.get("zone")).most_common(10):
        print(f"  {value:20s} {count:3d}")

    print_header("QUALIFIED LEADS (Beta = Oui)")
    leads = [r for r in data if r.get("beta_interest") == "yes" and r.get("qualified")]
    if leads:
        for r in leads[:10]:
            print(f"  {r.get('email', 'N/A'):25s} | {r.get('zone', 'N/A'):15s} | {r.get('phone', 'N/A') or 'No phone'}")
    else:
        print("  Aucun lead qualifie.")

    print_header("RECENT RESPONSES (last 5)")
    for r in data[:5]:
        date = r.get("created_at", "N/A")[:10]
        role = LABELS["role"].get(r.get("role"), r.get("role", "N/A"))
        problem = LABELS["main_problem"].get(r.get("main_problem"), r.get("main_problem", "N/A"))
        print(f"  {date} | {role:10s} | {problem:15s} | {r.get('zone', 'N/A')}")

    print("\n" + "=" * 60)


def pct(part, total):
    return f"{part / total * 100:.1f}%" if total > 0 else "0%"


def main():
    data = fetch_responses()
    analyze(data)

    # Export to CSV if pandas available
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        csv_path = f"hermes_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nExported to: {csv_path}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
