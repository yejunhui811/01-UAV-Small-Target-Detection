# Experiment records

현재 실제 실험은 없으며 [template.md](template.md)는 미실행 양식이다.

실험별 기록은 `experiments/<experiment-id>/README.md`, 설정은 `configs/<experiment-id>.toml`에 둔다. ID 예: `exp-001-yolo-baseline` (이름 예시이며 실행된 실험이 아니다).

1. 실행 전 hypothesis와 비교 대상, 변경 변수, 설정, seed를 기록한다.
2. [설정 양식](../configs/experiment.example.toml)을 채우고 dataset 및 model의 정확한 버전을 기록한다.
3. 정확한 command, code commit, 환경과 실행 시작/종료 시각을 기록한다.
4. raw logs, prediction과 weights는 Git에서 제외한 `outputs/<experiment-id>/`에 저장한다. 필요하면 외부 보관 위치와 checksum을 기록한다.
5. 실제 output에서 확인한 metric만 기록하고 작은 결과 표·figure를 `results/`에 추가한다.
6. failure cases, 해석, 한계와 conclusion을 남긴다. 실패·중단·미측정 상태를 숨기지 않는다.

상태 예: `planned` → `running` → `completed` 또는 `failed` / `interrupted`. dataset, evaluator와 timing 조건이 다른 실험을 같은 조건으로 비교하지 않는다. 측정 정의는 [평가 정책](../docs/evaluation.md)을 참고한다.
