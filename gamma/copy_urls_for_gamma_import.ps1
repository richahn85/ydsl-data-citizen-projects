param(
    [int]$Start = 1,
    [int]$Limit = 0,
    [string]$CsvPath = ".\gamma\lesson_page_urls.csv"
)

$rows = Import-Csv -LiteralPath $CsvPath | Where-Object { [int]$_.project_no -ge $Start }
if ($Limit -gt 0) {
    $rows = $rows | Select-Object -First $Limit
}

Write-Host "Gamma 웹 가져오기 보조 모드입니다."
Write-Host "각 교안 URL을 클립보드에 복사합니다. Gamma Import 화면의 URL 입력칸에 붙여넣고 생성 시작 후 Enter를 누르세요."
Write-Host ""

foreach ($row in $rows) {
    Set-Clipboard -Value $row.lesson_url
    Write-Host "[$($row.project_no)] $($row.title)"
    Write-Host $row.lesson_url
    Write-Host "URL이 클립보드에 복사되었습니다."
    Start-Process "https://gamma.app/"
    Read-Host "Gamma에 넣은 뒤 Enter"
}

Write-Host "완료"
