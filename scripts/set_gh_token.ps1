# set_gh_token.ps1 — pose un fine-grained PAT sans jamais l'afficher ni le logger.
# Usage : powershell -ExecutionPolicy Bypass -File scripts\set_gh_token.ps1
# Le token est demande en masque (****), pipe direct dans gh, variable nettoyee.
$ErrorActionPreference = "Stop"
Write-Host "Colle ton github_pat_... quand demande (saisie masquee, rien ne s'affiche)."
$sec = Read-Host "Token" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try {
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
  if ([string]::IsNullOrWhiteSpace($plain)) { throw "Token vide, abandon." }
  $plain | gh auth login --with-token --hostname github.com
} finally {
  if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
  Remove-Variable sec -ErrorAction SilentlyContinue
  if (Get-Variable plain -ErrorAction SilentlyContinue) { Remove-Variable plain -ErrorAction SilentlyContinue }
}
Write-Host "--- VERIF ---"
gh auth status
