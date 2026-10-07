# Dependency strategy

초기 개발 기준은 Python 3.11이다. bootstrap 환경에 설치되어 있고 TOML을 표준 라이브러리 `tomllib`로 읽을 수 있어, 현재 구조 검증에 별도 패키지가 필요하지 않다. 이는 향후 모든 모델·GPU 환경과의 호환성을 보장하는 선택이 아니다.

`requirements.txt`는 현재 주석만 포함한다. PyTorch, Ultralytics, RT-DETR 관련 패키지는 baseline 구현 시 실제 사용할 구현체와 CPU/GPU 환경을 정하고 호환성을 검증한 뒤 추가한다. 불필요한 패키지를 미리 설치하지 않는다.

향후 dependency 도입 시:
1. 기능에 필요한 직접 dependency와 검증한 버전을 `requirements.txt`에 기록한다.
2. 모델 framework, Python, CUDA/driver의 조합을 실제 환경에서 확인한다. 장치별 설치 방식이 다르면 별도 파일과 명령으로 문서화한다.
3. 각 실행 환경의 transitive dependency snapshot을 기록한다. 경로·private index·token이 포함되지 않았는지 검토한다.
4. `pip check`, import 및 필요한 sample 실행을 검증하고 환경 정보를 실험 기록에 연결한다.

현재 파일은 완전한 환경 lock이 아니다. 모델 실행 전에는 검증된 버전 pin과 환경 snapshot을 갖춘다. `.venv/`는 로컬 전용이며 commit하지 않는다.
