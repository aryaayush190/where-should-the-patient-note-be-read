# Convert the submission .docx to PDF with Microsoft Word and report the page count.
#   powershell -ExecutionPolicy Bypass -File paper/docx_to_pdf.ps1 [-Name TELMED2027_submission_v2]
# Uses its own hidden Word instance (does not touch documents the user has open) and kills only that
# instance if it does not finish within 150 s (e.g. a hidden repair dialog).
param([string]$Name = "TELMED2027_submission")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here "$Name.docx"
$dst = Join-Path $here "$Name.pdf"
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$job = Start-Job -ScriptBlock {
  param($src, $dst)
  $w = New-Object -ComObject Word.Application
  $w.Visible = $false
  $w.DisplayAlerts = 0
  try {
    $d = $w.Documents.Open($src, $false, $true, $false)
    $d.Repaginate()
    $pages = $d.ComputeStatistics(2)
    $d.ExportAsFixedFormat($dst, 17)
    $d.Close([ref]0)
    "pages: $pages"
  } finally { $w.Quit() }
} -ArgumentList $src, $dst
if (Wait-Job $job -Timeout 150) {
  Receive-Job $job
} else {
  "TIMEOUT: Word did not finish; stopping only the Word instance started by this script"
  Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | Stop-Process -Force
  Stop-Job $job
}
Remove-Job $job -Force
