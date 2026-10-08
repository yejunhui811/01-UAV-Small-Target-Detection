# Source code

`uav_small_target/`는 프로젝트의 Python package이다. `visdrone_validation.py`에 읽기 전용 파일 대응·annotation metadata와 선택적인 이미지 decoding·bbox 경계 검사 API가 있으며, CLI는 `scripts/validate_visdrone.py`를 사용한다. 자세한 범위와 한계는 [validator 안내](../docs/visdrone-validation.md)에 있다.

`yolo_experiment.py`는 모델 dependency를 import하지 않는 설정 검사·hash·subset 선택·GT 변환·고정 confidence matching을 제공한다. 선택적인 `coco_metrics()`만 pycocotools/numpy를 import한다. 실제 학습·validation·timing은 `scripts/run_yolo_experiment.py`에서 Ultralytics를 필요할 때 import한다. [YOLO baseline 안내](../docs/yolo-baseline.md)를 따른다.

`visdrone_yolo.py`는 공통 parser를 사용해 로컬 train/val과 선택적인 test-dev를 YOLO 형식으로 변환한다. 원본 이미지 bytes와 annotation provenance를 보존하며 입력 오류가 있으면 중단한다. [변환 정책](../docs/visdrone-yolo.md)을 따른다.

`visdrone_annotations.py`는 validator와 preview가 공유하는 표준 라이브러리 기반 GT parser이다. `visdrone_preview.py`는 한 image/TXT pair의 bbox·class·검토 경고를 PNG/JSON으로 저장한다. [Preview 안내](../docs/visdrone-preview.md)를 따른다.

변환 v2는 기본 strict 동작을 유지하며 명시적인 0면적 제외 옵션만 추가했다. 실제 train/val 준비·audit는 [snapshot 기록](../docs/datasets/visdrone2019-det-2026-10-08/README.md)에 있다.
