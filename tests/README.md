# Tests

`test_yolo_experiment.py`는 실행 설정·오타·pilot subset 금지·경로 이탈·seed 선택, 원본 면적 GT 및 제외 행, one-to-one class matching, confidence cutoff와 IoU를 확인한다. metric dependency가 있으면 추가로 NumPy scalar JSON 기록 및 NaN 거부, 실제 pycocotools의 perfect/empty prediction·custom maxDet·GT 없는 면적 구간을 검증한다. CI는 작은 CPU-only `requirements-metrics.txt`를 설치하여 이 검사까지 실행하고 PyTorch/모델/실제 데이터를 사용하지 않는다. Pillow만 설치한 로컬 환경은 optional metric 테스트 2개를 skip하며 표시한다. 전체 모델 환경 검증은 `.venv-yolo/bin/python -B -m unittest discover -s tests -v`를 사용한다. 합성 unit test는 모델 학습을 실행하지 않는다.

`test_visdrone_extraction.py`는 합성 ZIP으로 경로 이탈·symlink·case collision 거부, CRC extraction과 파일 hash 기록, 원본 보존, 기존 output 보호, 뒤늦은 archive 오류 시 output 미공개를 확인한다. CI에서는 실제 ZIP을 다운로드하지 않는다.

`test_visdrone_preparation_audit.py`는 합성 ZIP → extraction → 변환 → audit 전체 흐름과 원본·복사 이미지·label 변경, 예상 외 파일 검출을 확인한다. `test_visdrone_yolo.py`는 v2의 명시적인 0면적 제외·원본 행 보존도 검사하며 기본 strict 검사는 유지한다.

저장소 root에서 Pillow를 설치한 가상환경으로 전체 테스트를 실행:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
```

`test_visdrone_validation.py`는 Python 표준 라이브러리로 작은 PNG와 TXT를 임시 폴더에 생성하고 종료 시 제거한다. 정상 metadata, 잘못된 필드·숫자·enum·bbox, missing pairs, 이름 충돌, 빈 파일, UTF-8 오류, exact duplicates, CLI 종료 코드·JSON, 원본 보존과 report 덮어쓰기 방지를 검증한다. fixture는 synthetic이며 실제 VisDrone 샘플이나 연구 결과가 아니다.

`test_visdrone_images.py`는 Pillow로 임시 PNG/JPEG를 생성한다. 픽셀 decoding, PNG checksum·압축 스트림 오류, 잘린 JPEG, 경계 밖 bbox·정확한 경계·소수 좌표, EXIF 원본 좌표계, multi-frame 거부, 픽셀 제한, 누락·충돌·decoding 실패에 따른 bbox 검사 생략, 원본 보존, CLI 옵션·dependency 오류를 검증한다.

Pillow 없이 기존 metadata 테스트만 확인할 때는 `python3 -B -m unittest discover -s tests -p test_visdrone_validation.py -v`를 사용한다. 전체 테스트는 Pillow가 필요하다. GPU/모델 실행, 실제 VisDrone dataset와 공식 evaluator는 테스트하지 않는다. 각 검증 범위는 [validator 안내](../docs/visdrone-validation.md)를 따른다.

[GitHub Actions CI](../docs/ci.md)는 Ubuntu 24.04 / Python 3.11에서 전체 합성 테스트, site packages 없는 metadata 테스트와 구조 검증을 실행한다. 실제 성공 여부는 해당 commit의 PR Checks 또는 Actions 로그를 확인한다.

`test_visdrone_preview.py`는 시각화의 실제 pixel 좌표·색상과 원본 SHA-256, class/ignore 의미, 경계·소수·offscreen, validator/parser 오류 일치, partial·empty preview, 손상/UTF-8, EXIF 원본 크기, raw/symlink·overwrite 보호, CLI·dependency와 반복 출력 일치를 합성 pair로 확인한다. 실제 VisDrone 그림은 생성하지 않는다.

`test_visdrone_yolo.py`는 합성 train/val/test-dev pair로 정규화 좌표 round-trip, 10개 class mapping·ignored/other 보존, 정밀도·빈 label, 원본/input/output hash·반복성, 잘못된 입력 뒤 output 미공개, decoding/EXIF·split·case collision·symlink·동시 output 생성 보호와 CLI를 확인한다. trainer와 공식 evaluator는 실행하지 않는다.
