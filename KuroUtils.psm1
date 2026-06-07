# KuroUtils.psm1 -- Centralized utilities for Kuro Rules management

$script:OWNED_ORGS = @(
    "github.com/Lemniscate-world/",
    "github.com/Lemniscate-SHA-256/",
    "github.com/pbakaus/"
)

$script:EXTERNAL_ORGS = @(
    "github.com/Demeter-Financial-Labs/"
)

function Get-KuroProjectOwnership {
    <#
    .SYNOPSIS
        Classifies a project as OWNED, EXTERNAL, or UNKNOWN by inspecting git remotes.
    .DESCRIPTION
        Returns 'OWNED' if any remote matches an owned org, 'EXTERNAL' if any matches
        an external org, 'UNKNOWN' otherwise (no remote or unknown org).
        First match wins: OWNED > EXTERNAL > UNKNOWN.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectPath
    )

    if (-not (Test-Path (Join-Path $ProjectPath ".git"))) {
        return "UNKNOWN"
    }

    $remotes = & git -C $ProjectPath remote -v 2>$null
    if (-not $remotes) { return "UNKNOWN" }

    foreach ($org in $script:OWNED_ORGS) {
        if ($remotes -match [regex]::Escape($org)) { return "OWNED" }
    }
    foreach ($org in $script:EXTERNAL_ORGS) {
        if ($remotes -match [regex]::Escape($org)) { return "EXTERNAL" }
    }
    return "UNKNOWN"
}

function Get-KuroProjects {
    <#
    .SYNOPSIS
        Returns a list of project directories tracked by Kuro.
    .DESCRIPTION
        Each returned object includes Name, Path, and Ownership ('OWNED' | 'EXTERNAL' | 'UNKNOWN').
    #>
    [CmdletBinding()]
    param()

    $RULES_DIR = $PSScriptRoot
    $DOCS_DIR = Split-Path -Parent $RULES_DIR
    $excludeFile = Join-Path $RULES_DIR "exclude.txt"
    $projectsFile = Join-Path $RULES_DIR "projects.txt"

    $excluded = @("kuro-rules")
    if (Test-Path $excludeFile) {
        $excluded += Get-Content $excludeFile | Where-Object { $_ -and $_ -notmatch "^\s*#" } | ForEach-Object { $_.Trim() }
    }

    $projects = @()

    # Priority 1: projects.txt
    if (Test-Path $projectsFile) {
        $projectNames = Get-Content $projectsFile | Where-Object { $_ -and $_ -notmatch "^\s*#" } | ForEach-Object { $_.Trim() }
        foreach ($name in $projectNames) {
            $path = Join-Path $DOCS_DIR $name
            if (Test-Path $path) {
                $ownership = Get-KuroProjectOwnership -ProjectPath $path
                $projects += [PSCustomObject]@{
                    Name      = $name
                    Path      = $path
                    Ownership = $ownership
                }
            }
        }
    }

    # Priority 2: Auto-discovery for any .git repo in Documents
    $allDirs = Get-ChildItem -Path $DOCS_DIR -Directory -ErrorAction SilentlyContinue
    foreach ($dir in $allDirs) {
        if ((Test-Path (Join-Path $dir.FullName ".git")) -and ($excluded -notcontains $dir.Name)) {
            # Avoid duplicates if already in projects.txt
            if ($projects.Name -notcontains $dir.Name) {
                $ownership = Get-KuroProjectOwnership -ProjectPath $dir.FullName
                $projects += [PSCustomObject]@{
                    Name      = $dir.Name
                    Path      = $dir.FullName
                    Ownership = $ownership
                }
            }
        }
    }

    return $projects
}

function Write-KuroLog {
    param([string]$Message, [string]$Color = "Gray")
    Write-Host "[Kuro] $Message" -ForegroundColor $Color
}

Export-ModuleMember -Function Get-KuroProjects, Get-KuroProjectOwnership, Write-KuroLog
