
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$FlociEndpoint = "http://localhost:4566",
    [string]$Region = "us-east-1",
    [switch]$RunTests,
    [switch]$CheckHttp
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$env:AWS_PAGER = ""

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path
$ReportDir = Join-Path $ProjectRoot "completion-audit"
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ReportPath = Join-Path $ReportDir "talentmatch-completion-audit-$Stamp.txt"
$script:Results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param(
        [string]$Area,
        [string]$Check,
        [ValidateSet("PASS","WARNING","FAIL","NOT VERIFIED","INFO")]
        [string]$Status,
        [string]$Details
    )
    $script:Results.Add([pscustomobject]@{
        Area = $Area
        Check = $Check
        Status = $Status
        Details = ($Details -replace "`r?`n"," ")
    }) | Out-Null
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-AwsJson {
    param([string[]]$Arguments)

    if (-not (Test-Command "aws")) { return $null }

    $awsArgs = @("--endpoint-url",$FlociEndpoint,"--region",$Region) + $Arguments
    $raw = & aws @awsArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{_error=(($raw | Out-String).Trim())}
    }

    try {
        return ($raw | Out-String | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        return [pscustomobject]@{_error="Command returned non-JSON output."}
    }
}

function Add-CommandResult {
    param(
        [string]$Area,
        [string]$Check,
        [string]$CommandName
    )

    if (Test-Command $CommandName) {
        Add-Result $Area $Check "PASS" "$CommandName is installed."
    }
    else {
        Add-Result $Area $Check "FAIL" "$CommandName was not found in PATH."
    }
}

Write-Host "`nTalentMatch Cloud - consolidated completion audit" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Report:  $ReportPath`n"

# 1. Tooling
foreach ($cmd in @("docker","terraform","aws","python")) {
    Add-CommandResult "Environment" "$cmd availability" $cmd
}

# 2. Docker containers
if (Test-Command "docker") {
    $dockerInfo = & docker info --format "{{.ServerVersion}}" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Add-Result "Environment" "Docker daemon" "PASS" "Docker server version $dockerInfo."

        $containers = & docker ps -a --format "{{.Names}}|{{.Status}}|{{.Ports}}" 2>&1

        foreach ($name in @(
            "talentmatch_frontend",
            "talentmatch_app",
            "talentmatch_worker",
            "talentmatch_db",
            "floci",
            "floci-ui"
        )) {
            $line = $containers |
                Where-Object { $_ -like "$name|*" } |
                Select-Object -First 1

            if ($line) {
                $state = if ($line -match "\|Up ") { "PASS" } else { "WARNING" }
                Add-Result "Docker" "$name container" $state $line
            }
            else {
                Add-Result "Docker" "$name container" "WARNING" "Expected container name not found; Compose names may differ."
            }
        }
    }
    else {
        Add-Result "Environment" "Docker daemon" "FAIL" (($dockerInfo | Out-String).Trim())
    }
}

# 3. Optional HTTP probes
if ($CheckHttp) {
    foreach ($url in @(
        "http://localhost:5173",
        "http://localhost:8000/docs",
        "http://localhost:4500"
    )) {
        try {
            $r = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 5 -UseBasicParsing
            Add-Result "Application" $url "PASS" "HTTP $([int]$r.StatusCode)"
        }
        catch {
            Add-Result "Application" $url "WARNING" $_.Exception.Message
        }
    }
}
else {
    Add-Result "Application" "HTTP endpoint checks" "NOT VERIFIED" "Rerun with -CheckHttp to probe frontend, backend Swagger and Floci UI."
}

# 4. Floci and the nine agreed service areas
if (Test-Command "aws") {
    try {
        $health = Invoke-WebRequest -Uri $FlociEndpoint -Method Get -TimeoutSec 4 -UseBasicParsing
        Add-Result "Floci" "Endpoint reachability" "PASS" "HTTP $([int]$health.StatusCode) from $FlociEndpoint."
    }
    catch {
        Add-Result "Floci" "Endpoint reachability" "WARNING" "Endpoint root probe inconclusive; checking AWS APIs."
    }

    $s3 = Invoke-AwsJson @("s3api","list-buckets")

    if ($s3._error) {
        Add-Result "S3" "Bucket inventory" "FAIL" $s3._error
    }
    elseif ($s3.Buckets | Where-Object { $_.Name -eq "talentmatch-resumes-local" }) {
        Add-Result "S3" "Resume bucket" "PASS" "talentmatch-resumes-local exists."
    }
    else {
        Add-Result "S3" "Resume bucket" "WARNING" "Expected bucket not found."
    }

    $queues = Invoke-AwsJson @("sqs","list-queues")

    if ($queues._error) {
        Add-Result "SQS" "Queue inventory" "FAIL" $queues._error
    }
    else {
        $qText = $queues.QueueUrls -join " "

        foreach ($q in @(
            "talentmatch-local-resume-processing",
            "talentmatch-local-resume-processing-dlq"
        )) {
            if ($qText -match [regex]::Escape($q)) {
                Add-Result "SQS" $q "PASS" "Queue exists."
            }
            else {
                Add-Result "SQS" $q "WARNING" "Queue not found."
            }
        }
    }

    $table = Invoke-AwsJson @(
        "dynamodb","describe-table",
        "--table-name","talentmatch-resume-audit-local"
    )

    if ($table._error) {
        Add-Result "DynamoDB" "Audit table" "FAIL" $table._error
    }
    else {
        Add-Result "DynamoDB" "Audit table" "PASS" "Status=$($table.Table.TableStatus); ItemCount=$($table.Table.ItemCount)."
    }

    $fn = Invoke-AwsJson @(
        "lambda","get-function-configuration",
        "--function-name","talentmatch-resume-completed-local"
    )

    if ($fn._error) {
        Add-Result "Lambda" "Completion function" "FAIL" $fn._error
    }
    else {
        Add-Result "Lambda" "Completion function" "PASS" "State=$($fn.State); Runtime=$($fn.Runtime); Handler=$($fn.Handler)."
    }

    $rule = Invoke-AwsJson @(
        "events","describe-rule",
        "--name","talentmatch-resume-completed-local"
    )

    if ($rule._error) {
        Add-Result "EventBridge" "Completion rule" "FAIL" $rule._error
    }
    else {
        $targets = Invoke-AwsJson @(
            "events","list-targets-by-rule",
            "--rule","talentmatch-resume-completed-local"
        )

        if ($targets._error) {
            Add-Result "EventBridge" "Completion target" "WARNING" $targets._error
        }
        elseif ($targets.Targets.Count -gt 0) {
            Add-Result "EventBridge" "Completion target" "PASS" "Rule state=$($rule.State); target count=$($targets.Targets.Count)."
        }
        else {
            Add-Result "EventBridge" "Completion target" "WARNING" "Rule exists but has no targets."
        }
    }

    $logs = Invoke-AwsJson @(
        "logs","describe-log-groups",
        "--log-group-name-prefix","/aws/lambda/talentmatch-resume-completed-local"
    )

    if ($logs._error) {
        Add-Result "CloudWatch Logs" "Completion log group" "WARNING" $logs._error
    }
    elseif ($logs.logGroups.Count -gt 0) {
        Add-Result "CloudWatch Logs" "Completion log group" "PASS" "Log group exists; retention=$($logs.logGroups[0].retentionInDays) days."
    }
    else {
        Add-Result "CloudWatch Logs" "Completion log group" "WARNING" "Expected log group not found."
    }

    $iam = Invoke-AwsJson @(
        "iam","list-role-policies",
        "--role-name","talentmatch-completion-lambda-local-role"
    )

    if ($iam._error) {
        Add-Result "IAM" "Completion Lambda inline policies" "WARNING" $iam._error
    }
    elseif ($iam.PolicyNames.Count -ge 2) {
        Add-Result "IAM" "Completion Lambda inline policies" "PASS" "Found: $($iam.PolicyNames -join ', ')."
    }
    else {
        Add-Result "IAM" "Completion Lambda inline policies" "WARNING" "Found $($iam.PolicyNames.Count) inline policies."
    }

    # Optional EC2 demo infrastructure has been removed.
    Add-Result "EC2" "Optional demo instance" "NOT VERIFIED" "EC2 demo instance was removed; no active demo instance is expected."

    Add-Result "VPC / Security" "Optional demo infrastructure" "NOT VERIFIED" "Optional EC2 demo infrastructure is not included in the current verification."

}
else {
    Add-Result "AWS services" "Floci service inventory" "NOT VERIFIED" "AWS CLI unavailable."
}

# 5. Each Terraform root is inspected independently; no init/plan/apply/import/refresh.
if (Test-Command "terraform") {
    foreach ($folder in @("terraform","terraform/aws","terraform/floci")) {
        $path = Join-Path $ProjectRoot $folder

        if (-not (Test-Path $path)) {
            Add-Result "Terraform" "$folder directory" "WARNING" "Directory not found."
            continue
        }

        $tfFiles = @(Get-ChildItem -LiteralPath $path -Filter "*.tf" -File -ErrorAction SilentlyContinue)

        Add-Result "Terraform" "$folder configuration" $(if ($tfFiles.Count -gt 0) {"PASS"} else {"WARNING"}) "$($tfFiles.Count) .tf files found."

        $stateOutput = & terraform "-chdir=$folder" state list 2>&1

        if ($LASTEXITCODE -eq 0) {
            $managed = @($stateOutput | Where-Object { $_ -and $_ -notmatch "^data\." })
            Add-Result "Terraform" "$folder state" "PASS" "$($managed.Count) managed resource entries (data sources excluded)."
        }
        else {
            Add-Result "Terraform" "$folder state" "NOT VERIFIED" "No readable state or state command failed; this does not mean resources are absent."
        }
    }
}
else {
    Add-Result "Terraform" "State inventory" "NOT VERIFIED" "Terraform CLI unavailable."
}

# 6. Project docs, tests, GitHub workflows
foreach ($item in @(
    @{Name="README";Path="README.md"},
    @{Name="Docker Compose";Path="docker-compose.yml"},
    @{Name="Application tests";Path="tests"},
    @{Name="Floci Terraform";Path="terraform/floci"},
    @{Name="Git ignore";Path=".gitignore"}
)) {
    if (Test-Path (Join-Path $ProjectRoot $item.Path)) {
        Add-Result "Project files" $item.Name "PASS" "$($item.Path) exists."
    }
    else {
        Add-Result "Project files" $item.Name "WARNING" "$($item.Path) not found."
    }
}

$workflowDir = Join-Path $ProjectRoot ".github/workflows"

if (Test-Path $workflowDir) {
    $wc = @(Get-ChildItem $workflowDir -File -ErrorAction SilentlyContinue).Count
    Add-Result "CI/CD" "GitHub Actions workflows" $(if ($wc -gt 0) {"PASS"} else {"WARNING"}) "$wc workflow files found."
}
else {
    Add-Result "CI/CD" "GitHub Actions workflows" "WARNING" "No .github/workflows directory found."
}

if (Test-Path (Join-Path $ProjectRoot ".env")) {
    Add-Result "Security hygiene" ".env" "INFO" ".env exists locally; its contents were not read. Ensure Git ignores it."
}
else {
    Add-Result "Security hygiene" ".env" "INFO" "No root .env file found."
}

# 7. Optional existing test suite
if ($RunTests) {
    if (Test-Command "docker") {
        Write-Host "`nRunning existing pytest suite..." -ForegroundColor Yellow

        Push-Location $ProjectRoot

        try {
            $testOutput = & docker compose run --rm --no-deps talentmatch pytest -q 2>&1
            $testExit = $LASTEXITCODE
            $testText = ($testOutput | Out-String).Trim()

            if ($testExit -eq 0) {
                Add-Result "Tests" "pytest" "PASS" $testText
            }
            else {
                Add-Result "Tests" "pytest" "FAIL" $testText
            }
        }
        finally {
            Pop-Location
        }
    }
    else {
        Add-Result "Tests" "pytest" "NOT VERIFIED" "Docker unavailable."
    }
}
else {
    Add-Result "Tests" "pytest" "NOT VERIFIED" "Not run. Use -RunTests to execute the existing test suite."
}

# 8. Report
$lines = [System.Collections.Generic.List[string]]::new()

$lines.Add("TALENTMATCH CLOUD - COMPLETION AUDIT")
$lines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
$lines.Add("Project root: $ProjectRoot")
$lines.Add("Floci endpoint: $FlociEndpoint")
$lines.Add("")

$lines.Add("SUMMARY")

foreach ($group in ($script:Results | Group-Object Status | Sort-Object Name)) {
    $lines.Add("$($group.Name): $($group.Count)")
}

$lines.Add("")
$lines.Add("DETAILS")

foreach ($r in $script:Results) {
    $lines.Add("[$($r.Status)] $($r.Area) / $($r.Check) - $($r.Details)")
}

$lines.Add("")
$lines.Add("Safety: No infrastructure create/update/delete, Terraform apply/import/destroy/refresh, or secret reads were performed.")
$lines.Add("Note: Resource existence does not prove end-to-end behaviour.")

$lines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host "`n===== AUDIT SUMMARY =====" -ForegroundColor Cyan

foreach ($group in ($script:Results | Group-Object Status | Sort-Object Name)) {
    $color = switch ($group.Name) {
        "PASS" {"Green"}
        "WARNING" {"Yellow"}
        "FAIL" {"Red"}
        default {"Gray"}
    }

    Write-Host ("{0,-14} {1}" -f $group.Name,$group.Count) -ForegroundColor $color
}

Write-Host "`nDetailed report saved to: $ReportPath" -ForegroundColor Green
Write-Host "No infrastructure resources were created, changed, or deleted." -ForegroundColor Cyan
