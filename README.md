# YDSL 데이터 시민 프로젝트 30

이 저장소는 `YDSL 데이터 시민 프로젝트 30 Obsidian Wiki`를 GitHub Pages에서 볼 수 있도록 변환한 정적 웹사이트입니다.

- 30개 프로젝트별 강의 교안
- 프로젝트 보고서/데이터/SPSS 노트의 웹 버전
- 주제 지도와 데이터 활용 패턴
- 주요 시각화 이미지

원본 CSV/XLSX/DOCX/SPSS/PDF 파일은 공개 저장소에 포함하지 않았고, 로컬 Obsidian vault에 보관합니다.

## 지식 그래프

Obsidian vault의 내부 링크 관계를 웹에서 볼 수 있도록 `graph.html`과 `graph-data.json`을 추가했습니다.

- 공개 URL: `https://richahn85.github.io/ydsl-data-citizen-projects/graph.html`
- 데이터 생성: `python build_graph_data.py`

## Gamma AI PPT 자동화

30개 개별 강의 교안 URL을 Gamma AI에 순차적으로 넣을 수 있도록 `gamma/` 폴더를 추가했습니다.

- `gamma/lesson_page_urls.csv`: 교안 30개 URL 큐
- `gamma/run_gamma_from_urls.py`: Gamma API로 30개 PPTX를 순차 생성하는 스크립트
- `gamma/run_gamma_interactive.ps1`: API 키를 입력받아 PowerShell에서 1개씩 확인하며 실행하는 스크립트
- `gamma/copy_urls_for_gamma_import.ps1`: Gamma 웹 화면에 URL을 하나씩 넣을 때 쓰는 클립보드 보조 스크립트

자세한 실행법은 `gamma/README.md`를 보세요.
