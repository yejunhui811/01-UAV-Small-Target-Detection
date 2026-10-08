# Scripts

저장소 root에서 `python3 scripts/validate_structure.py`를 실행하면 기반 구조, 로컬 문서 링크, TOML parsing, ignore 규칙과 staged 파일을 확인한다. 외부 패키지 설치, 네트워크 접근, 데이터 다운로드, 학습을 수행하지 않는다.

`python scripts/run_yolo_experiment.py --help`는 YOLO11n 학습 → validation → 원본 면적 COCO AP_small → 고정 operating point P/R·failure 집계 → 동기화 timing을 한 run에 기록한다. `requirements-yolo.txt`를 설치하고 [baseline 안내](../docs/yolo-baseline.md)의 설정·실행 명령을 따른다. `--dry-run`은 표준 라이브러리로 설정만 검증하며 실제 실행은 기존 run을 덮어쓰지 않는다.

`python scripts/extract_visdrone.py --help`로 이미 다운로드한 train/val ZIP의 안전한 extraction과 CRC·파일 hash 기록을 실행할 수 있다. 기존 output을 덮어쓰지 않는다. [준비 안내](../docs/visdrone-extraction.md)를 따른다.

`python scripts/audit_visdrone_preparation.py --help`는 extraction file manifest와 변환 sidecar를 대조해 원본 보존·이미지 복사·label hash·전체 target 좌표 round-trip을 검사한다. 실제 준비 기록에 범위와 tolerance를 기록한다. 모델이나 공식 evaluator는 실행하지 않는다.

`python scripts/convert_visdrone_yolo.py --help`로 로컬 VisDrone → YOLO 변환 도움말을 볼 수 있다. 합성 `--demo`, 원본 class/ignore 보존과 strict bbox 정책, output·종료 코드는 [변환 안내](../docs/visdrone-yolo.md)를 따른다. 합성 테스트와 실제 train/val 변환 v2·audit를 실행했다.

`python3 scripts/validate_visdrone.py --help`로 VisDrone 파일 대응·annotation metadata 검사 도움말을 볼 수 있다. Pillow 설치 후 `--check-images`로 이미지 decoding·bbox 경계 검사를 선택할 수 있다. 실제 데이터 준비 후의 실행 예시, report와 exit code는 [validator 안내](../docs/visdrone-validation.md)를 따른다. 실제 train/val 검사 결과는 [snapshot 기록](../docs/datasets/visdrone2019-det-2026-10-08/README.md)에 있다.

`python scripts/preview_visdrone.py --help`로 한 pair의 annotation 시각화 도움말을 볼 수 있다. 데이터 없는 `--demo`와 실제 데이터 준비 후의 사용 예시는 [preview 안내](../docs/visdrone-preview.md)를 따른다. output은 새 directory에만 저장하고 `outputs/`에 보관한다.
