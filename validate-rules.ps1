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

# 3. Check for Rule Gaps/Duplicates (basenames, pas numeros — redirector)
$basenames = @()
foreach ($file in $ruleFiles) {
    if ($file.BaseName -match "^(rule_.+)$") {
        $basenames += $Matches[1]
    }
}
$duplicates = $basenames | Group-Object | Where-Object { $_.Count -gt 1 }
if ($duplicates) {
    foreach ($d in $duplicates) {
        Write-KuroLog "  [FAIL] Duplicate rule file found: $($d.Name)" -Color Red
        $errors++
    }
} else {
    Write-KuroLog "  [PASS] No duplicate rule files ($($basenames.Count) files)." -Color DarkGray
}

# 4. Verify AGENTS.md index matches rules/ folder (A2/B1)
$indexEntries = @(Select-String -LiteralPath $agentsFile -Pattern '^- \*\*(rule_[A-Za-z0-9_]+)\*\*' | ForEach-Object {
    if ($_ -match '\*\*(rule_[A-Za-z0-9_]+)\*\*') { $Matches[1] }
})
$missingFromIndex = @($basenames | Where-Object { $indexEntries -notcontains $_ })
$extraInIndex = @($indexEntries | Where-Object { $basenames -notcontains $_ })
if ($missingFromIndex.Count -gt 0) {
    Write-KuroLog "  [FAIL] Rules missing from AGENTS.md index: $($missingFromIndex -join ', ')" -Color Red
    $errors++
}
if ($extraInIndex.Count -gt 0) {
    Write-KuroLog "  [FAIL] Stale entries in AGENTS.md index: $($extraInIndex -join ', ')" -Color Red
    $errors++
}
if (($missingFromIndex.Count -eq 0) -and ($extraInIndex.Count -eq 0)) {
    Write-KuroLog "  [PASS] AGENTS.md index matches rules/ ($($indexEntries.Count) entries)." -Color DarkGray
}

# 5. Verify compliance template exists (A3 + C)
$templateFile = Join-Path $RULES_DIR "templates\kuro-compliance.yml"
if (-not (Test-Path $templateFile)) {
    Write-KuroLog "  [FAIL] templates/kuro-compliance.yml missing!" -Color Red
    $errors++
} else {
    $tpl = Get-Content $templateFile -Raw
    foreach ($gate in @("R76", "R101", "R39", "R64", "R91", "R30", "R112")) {
        if ($tpl -notmatch $gate) {
            Write-KuroLog "  [FAIL] Template missing gate $gate" -Color Red
            $errors++
        }
    }
    Write-KuroLog "  [PASS] Compliance template gates present." -Color DarkGray
}
$preTemplate = Join-Path $RULES_DIR "templates\.pre-commit-config.yaml"
if (-not (Test-Path $preTemplate)) {
    Write-KuroLog "  [FAIL] templates/.pre-commit-config.yaml missing (C/R112)!" -Color Red
    $errors++
} else {
    Write-KuroLog "  [PASS] Pre-commit template present (R112)." -Color DarkGray
}

# 6. Ownership registry sync: KuroUtils.psm1 <-> gen_x_posts.py (A1 regression guard)
$kuroUtils = Get-Content (Join-Path $RULES_DIR "KuroUtils.psm1") -Raw
$genX = Get-Content (Join-Path $RULES_DIR "scripts\gen_x_posts.py") -Raw
foreach ($marker in @("LambdaSection/", "Lemniscate-world/", "Quant-Search/", "Demeter-Financial-Labs")) {
    if ($kuroUtils -notmatch [regex]::Escape($marker)) {
        Write-KuroLog "  [FAIL] KuroUtils.psm1 missing ownership marker: $marker (A1)" -Color Red
        $errors++
    }
}
if ($genX -notmatch "OWNED_MARKERS") {
    Write-KuroLog "  [FAIL] gen_x_posts.py OWNED_MARKERS missing" -Color Red
    $errors++
} else {
    Write-KuroLog "  [PASS] Ownership registry present in both files." -Color DarkGray
}

# 7. Audit script redirector support (A2 regression guard)
$auditPy = Get-Content (Join-Path $RULES_DIR "audit-rules.py") -Raw
if ($auditPy -notmatch "REDIRECTOR_RE") {
    Write-KuroLog "  [FAIL] audit-rules.py missing REDIRECTOR_RE (A2)" -Color Red
    $errors++
} else {
    Write-KuroLog "  [PASS] audit-rules.py redirector support present." -Color DarkGray
}

# 8. Run python audit in repo mode when available (non-bloquant si python absent)
try {
    $py = Get-Command python -ErrorAction Stop
    $auditOut = & python (Join-Path $RULES_DIR "audit-rules.py") --mode repo --scope all 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-KuroLog "  [FAIL] audit-rules.py --mode repo FAILED:" -Color Red
        $auditOut | ForEach-Object { Write-KuroLog "    $_" -Color Red }
        $errors++
    } else {
        Write-KuroLog "  [PASS] audit-rules.py --mode repo passed." -Color DarkGray
    }
} catch {
    Write-KuroLog "  [WARN] python absent, audit repo saute." -Color Yellow
}

if ($errors -gt 0) {
    Write-KuroLog "Validation FAILED with $errors errors. Commit aborted." -Color Red
    exit 1
}

Write-KuroLog "Validation PASSED. Proceeding with commit." -Color Green
exit 0
