# Configuration

[experiment.example.toml](experiment.example.toml)은 실험 설정을 기록할 TOML 양식이다. Python 3.11의 표준 라이브러리 `tomllib`로 parsing할 수 있다. 이 양식 자체는 학습 설정으로 바로 실행할 수 없다.

실행 가능한 YOLO 설정은 [smoke](yolo-smoke.toml), [전체 데이터 1-epoch pilot](yolo-pilot.toml), [50-epoch baseline 계획](yolo-baseline.toml)이다. [실행 안내](../docs/yolo-baseline.md)의 용도·device·평가 정책을 따른다. baseline은 CUDA 0을 사용하므로 실제 GPU 환경을 준비한 뒤 실행한다. 설정 변경·재시도는 새로운 experiment ID로 기록한다.

실험 도입 시 양식을 `<experiment-id>.toml`로 복사하고 빈 값과 미정 항목을 채운다. 구현 시 필수 필드, 값 범위, CPU/GPU device 선택, CLI 연결을 검증한다. 로컬 절대 경로와 비밀정보는 commit하지 않는다. seed, resize/tiling/augmentation 및 evaluation 조건을 기록한다.

현재 로컬 50-epoch 본학습은 [yolo-baseline-mps.toml](yolo-baseline-mps.toml)의 MPS / batch 8을 사용한다. CUDA 계획(batch 16)은 변경하지 않고 별도로 유지한다. [본학습 실행 기록](../experiments/exp-003-yolo11n-baseline-mps/README.md)에서 job status와 최종 결과를 구분한다.
