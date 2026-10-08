# Source code

`uav_small_target/`는 프로젝트의 Python package이다. `visdrone_validation.py`에 읽기 전용 파일 대응·annotation metadata와 선택적인 이미지 decoding·bbox 경계 검사 API가 있으며, CLI는 `scripts/validate_visdrone.py`를 사용한다. 자세한 범위와 한계는 [validator 안내](../docs/visdrone-validation.md)에 있다.

향후 dataset loading, model adapters, inference, evaluation 코드를 이곳에 추가한다. 현재 학습·추론 구현은 없다.

`visdrone_yolo.py`는 공통 parser를 사용해 로컬 train/val과 선택적인 test-dev를 YOLO 형식으로 변환한다. 원본 이미지 bytes와 annotation provenance를 보존하며 입력 오류가 있으면 중단한다. [변환 정책](../docs/visdrone-yolo.md)을 따른다.

`visdrone_annotations.py`는 validator와 preview가 공유하는 표준 라이브러리 기반 GT parser이다. `visdrone_preview.py`는 한 image/TXT pair의 bbox·class·검토 경고를 PNG/JSON으로 저장한다. [Preview 안내](../docs/visdrone-preview.md)를 따른다.
