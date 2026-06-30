# Gamma 교안 URL 자동 투입

이 폴더는 공개된 30개 강의 교안 페이지를 Gamma AI에 순차적으로 넣기 위한 작업 큐입니다.

## 파일

- `lesson_page_urls.csv`: 30개 교안 페이지 URL 목록
- `lesson_page_urls.txt`: URL만 한 줄씩 모은 목록
- `generate_lesson_url_queue.py`: 사이트 파일에서 URL 목록을 다시 생성
- `run_gamma_from_urls.py`: URL을 순서대로 읽고 Gamma API로 PPTX 생성을 요청
- `copy_urls_for_gamma_import.ps1`: Gamma 웹 화면에 수동으로 넣을 때 쓰는 클립보드 보조 스크립트

## 권장 자동 실행

Gamma API 키를 발급한 뒤 PowerShell에서 실행합니다. API 키는 파일에 저장하지 말고 현재 터미널 환경 변수로만 넣으세요.

```powershell
cd "C:\Users\USER\Documents\New project\ydsl-data-citizen-projects-site"
$env:GAMMA_API_KEY="여기에_Gamma_API_Key"
python .\gamma\run_gamma_from_urls.py --dry-run --limit 1
python .\gamma\run_gamma_from_urls.py
```

실행이 끝나면 `gamma/gamma_results.csv`에 각 교안의 `gamma_url`, `export_url`, 다운로드 경로가 기록됩니다. 기본값은 10장짜리 16:9 PPTX입니다.

## 일부만 실행

```powershell
python .\gamma\run_gamma_from_urls.py --start 11 --limit 5
```

위 명령은 11번부터 5개 교안만 처리합니다. 이미 완료된 항목은 자동으로 건너뜁니다. 다시 만들고 싶으면 `--force`를 붙입니다.

## Gamma 웹 화면으로 처리할 때

API를 쓰지 않고 Gamma 웹의 Import/URL 입력 화면에 하나씩 넣고 싶을 때는 아래 스크립트가 URL을 차례대로 클립보드에 복사합니다.

```powershell
cd "C:\Users\USER\Documents\New project\ydsl-data-citizen-projects-site"
.\gamma\copy_urls_for_gamma_import.ps1
```

완전 자동 생성은 `run_gamma_from_urls.py` 방식이 더 안정적입니다.
