# Scripts

저장소 root에서 `python3 scripts/validate_structure.py`를 실행하면 기반 구조, 로컬 문서 링크, TOML parsing, ignore 규칙과 staged 파일을 확인한다. 외부 패키지 설치, 네트워크 접근, 데이터 다운로드, 학습을 수행하지 않는다.

향후 데이터 변환·학습·평가 CLI를 추가한다. 각 CLI는 실행 명령, 설정 파일, 결과 위치를 문서화해야 한다.

`python3 scripts/validate_visdrone.py --help`로 VisDrone 파일 대응·annotation metadata 검사 도움말을 볼 수 있다. Pillow 설치 후 `--check-images`로 이미지 decoding·bbox 경계 검사를 선택할 수 있다. 실제 데이터 준비 후의 실행 예시, report와 exit code는 [validator 안내](../docs/visdrone-validation.md)를 따른다. 현재 실제 데이터 검증은 미실행이다.

`python scripts/preview_visdrone.py --help`로 한 pair의 annotation 시각화 도움말을 볼 수 있다. 데이터 없는 `--demo`와 실제 데이터 준비 후의 사용 예시는 [preview 안내](../docs/visdrone-preview.md)를 따른다. output은 새 directory에만 저장하고 `outputs/`에 보관한다.
