# Configuration

[experiment.example.toml](experiment.example.toml)은 실험 설정을 기록할 TOML 양식이다. Python 3.11의 표준 라이브러리 `tomllib`로 parsing할 수 있다. 현재 모델 실행 코드가 없으며 이 파일은 학습 설정으로 바로 실행할 수 없다.

실험 도입 시 양식을 `<experiment-id>.toml`로 복사하고 빈 값과 미정 항목을 채운다. 구현 시 필수 필드, 값 범위, CPU/GPU device 선택, CLI 연결을 검증한다. 로컬 절대 경로와 비밀정보는 commit하지 않는다. seed, resize/tiling/augmentation 및 evaluation 조건을 기록한다.
