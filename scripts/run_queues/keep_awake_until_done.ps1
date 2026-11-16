# Holds an idle-sleep exemption (SetThreadExecutionState, as media players do) until the overnight job
# writes its done marker. Changes no power settings; the exemption ends when this process exits.
param([string]$StatusFile = "runtime/queue_review.status", [string]$Marker = "full20b_done", [int]$MaxHours = 16)
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
$ES_CONTINUOUS = [uint32]2147483648; $ES_SYSTEM_REQUIRED = [uint32]1
$deadline = (Get-Date).AddHours($MaxHours)
while ((Get-Date) -lt $deadline) {
    [W.P]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) | Out-Null
    if ((Test-Path $StatusFile) -and (Select-String -Path $StatusFile -Pattern $Marker -Quiet)) { break }
    Start-Sleep -Seconds 60
}
[W.P]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
