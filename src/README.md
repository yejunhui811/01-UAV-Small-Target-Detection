# Source code

`uav_small_target/`는 프로젝트의 Python package이다. `visdrone_validation.py`에 읽기 전용 파일 대응·annotation metadata와 선택적인 이미지 decoding·bbox 경계 검사 API가 있으며, CLI는 `scripts/validate_visdrone.py`를 사용한다. 자세한 범위와 한계는 [validator 안내](../docs/visdrone-validation.md)에 있다.

향후 dataset loading/conversion, model adapters, inference, evaluation 코드를 이곳에 추가한다. 현재 학습·추론 구현은 없다.
