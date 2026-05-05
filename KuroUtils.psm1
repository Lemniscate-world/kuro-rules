# KuroUtils.psm1 -- Centralized utilities for Kuro Rules management

function Get-KuroProjects {
    <#
    .SYNOPSIS
        Returns a list of project directories tracked by Kuro.
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
                $projects += [PSCustomObject]@{
                    Name = $name
                    Path = $path
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
                $projects += [PSCustomObject]@{
                    Name = $dir.Name
                    Path = $dir.FullName
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

Export-ModuleMember -Function Get-KuroProjects, Write-KuroLog
