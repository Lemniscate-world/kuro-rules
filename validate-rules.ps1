# validate-rules.ps1 -- Safety check for Kuro Rules before commit

$RULES_DIR = Get-Location
Import-Module (Join-Path $RULES_DIR "KuroUtils.psm1") -Force

Write-KuroLog "Starting pre-commit validation..." -Color Cyan

$errors = 0

# 1. Verify AGENTS.md is a redirector
$agentsFile = Join-Path $RULES_DIR "AGENTS.md"
$content = Get-Content $agentsFile -Raw
if ($content -notmatch "Redirector") {
    Write-KuroLog "  [FAIL] AGENTS.md is NOT a redirector! It must not contain the full ruleset or other data." -Color Red
    $errors++
} else {
    Write-KuroLog "  [PASS] AGENTS.md redirector verified." -Color DarkGray
}

# 2. Verify Encodings (UTF-8)
$ruleFiles = Get-ChildItem (Join-Path $RULES_DIR "rules") -Filter "*.md"
foreach ($file in $ruleFiles) {
    # Check if file has BOM or is just plain UTF-8
    # Note: PowerShell 5.1 Get-Content can be tricky with encodings, but we check for common UTF-16 indicators
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Count -gt 2 -and $bytes[0] -eq 0xff -and $bytes[1] -eq 0xfe) {
        Write-KuroLog "  [FAIL] $($file.Name) is UTF-16! Must be UTF-8." -Color Red
        $errors++
    }
}

# 3. Check for Rule Gaps/Duplicates
$numbers = @()
foreach ($file in $ruleFiles) {
    if ($file.Name -match "rule_(\d+)") {
        $numbers += [int]($Matches[1])
    }
}
$duplicates = $numbers | Group-Object | Where-Object { $_.Count -gt 1 }
if ($duplicates) {
    foreach ($d in $duplicates) {
        Write-KuroLog "  [FAIL] Duplicate rule number found: $($d.Name)" -Color Red
        $errors++
    }
}

if ($errors -gt 0) {
    Write-KuroLog "Validation FAILED with $errors errors. Commit aborted." -Color Red
    exit 1
}

Write-KuroLog "Validation PASSED. Proceeding with commit." -Color Green
exit 0
