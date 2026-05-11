import os
import re
import sys
from pathlib import Path

# Paths
DOCUMENTS_DIR = Path(os.path.expanduser("~/Documents"))
PROFILE_README_PATH = DOCUMENTS_DIR / "Lemniscate-world" / "README.md"
SESSION_SUMMARY_PATH = Path("SESSION_SUMMARY.md")

def get_current_project_info():
    """Extract project name and latest progress percentage from SESSION_SUMMARY.md."""
    if not SESSION_SUMMARY_PATH.exists():
        return None, None
        
    project_name = Path(os.getcwd()).name
    content = SESSION_SUMMARY_PATH.read_text(encoding="utf-8")
    
    # Extract the first Progress: X% from the file (since we prepend latest)
    match = re.search(r"\*\*Progress\*\*:\s*(\d+)%", content)
    if match:
        return project_name, match.group(1)
    return project_name, None

def update_profile_readme(project_name, progress):
    """Update the profile README with the new progress percentage."""
    if not PROFILE_README_PATH.exists():
        print(f"[-] Profile README not found at {PROFILE_README_PATH}")
        return False
        
    content = PROFILE_README_PATH.read_text(encoding="utf-8")
    
    # 1. Update Section List (handles various prefixes like ╬)
    # Pattern: [Non-alphanumeric chars]Section-X (...) : ProjectName (X%)
    pattern_sec = rf"({project_name}\s*\()(\d+)(%%)"
    if re.search(pattern_sec, content):
        content = re.sub(pattern_sec, rf"\g<1>{progress}\g<3>", content)
        print(f"[+] Updated {project_name} to {progress}% in Section List.")
    else:
        # Fallback search for the line containing the project name and a percentage
        lines = content.splitlines()
        new_lines = []
        found = False
        for line in lines:
            if project_name in line and not found:
                new_line = re.sub(r"(\d+)%", f"{progress}%", line)
                if new_line != line:
                    new_lines.append(new_line)
                    found = True
                    print(f"[+] Updated {project_name} to {progress}% via line fallback.")
                    continue
            new_lines.append(line)
        content = "\n".join(new_lines)

    # 2. Update Focus Projects section
    # Pattern: [ProjectName](url) ... [X% - description]
    pattern_focus = rf"(\[({project_name})\]\(.*?\).*?\[)(\d+)(%%)"
    if re.search(pattern_focus, content):
        content = re.sub(pattern_focus, rf"\g<1>{progress}\g<4>", content)
        print(f"[+] Updated {project_name} to {progress}% in Focus Projects.")
    else:
        # Try a more relaxed match for the Focus section
        pattern_relaxed = rf"(\[({project_name})\]\(.*?\).*?)(\d+)%"
        if re.search(pattern_relaxed, content):
            content = re.sub(pattern_relaxed, rf"\g<1>{progress}%", content)
            print(f"[+] Updated {project_name} to {progress}% in Focus Projects (relaxed match).")
        else:
            print(f"[!] Could not find {project_name} in Focus Projects section.")

    PROFILE_README_PATH.write_text(content, encoding="utf-8")
    return True

if __name__ == "__main__":
    print("[*] Starting Kuro Profile Sync...")
    p_name, p_progress = get_current_project_info()
    
    if p_name and p_progress:
        print(f"[*] Detected Project: {p_name} | Progress: {p_progress}%")
        if update_profile_readme(p_name, p_progress):
            print("[+] Sync complete.")
        else:
            print("[-] Sync failed.")
    else:
        print("[-] Could not detect project info or progress in SESSION_SUMMARY.md")
        sys.exit(1)
