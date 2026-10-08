# YOLO11n local pipeline validation

**목적: 32 train / 8 val subset으로 실행 경로를 검증합니다. 연구 baseline 결과가 아닙니다.** seed 42, imgsz 320, batch 4, 1 epoch, MPS FP32를 사용했습니다. [최종 smoke 설정](../../configs/yolo-smoke.toml)과 [실행 정책](../../docs/yolo-baseline.md)을 따릅니다.

## Executions and fixes

| Run ID | Actual status | Observation |
| --- | --- | --- |
| `exp-001-yolo11n-smoke-mps` | failed | 지원하지 않는 framework settings key를 사용하여 학습 전 중단. 지원되는 key로 수정하고 settings parent를 먼저 생성하도록 수정 |
| `exp-001-yolo11n-smoke-mps-v2` | failed | MPS 학습과 validation 완료 후 NumPy int64 JSON 기록 오류. scalar 변환·NaN 거부를 구현하고 regression test 추가 |
| `exp-001-yolo11n-smoke-mps-v3` | completed | 학습·checkpoint·validation·원본 면적 COCO AP·failure matching·동기화 timing·JSON 기록 전체 완료 |

실패한 run은 보존했고 새 ID로 재시도했습니다. weights, subset 이미지/label, 원본 output과 상세 metric은 ignored `outputs/<run-id>/`에 있습니다. CPU에서도 v3 checkpoint와 실제 val 이미지 한 장의 inference를 실행했습니다(`outputs/cpu-forward-check/report.json`). CPU 학습과 CUDA 실행은 검증하지 않았습니다.

각 run은 source/config/dataset/weights SHA-256, Git base commit·dirty 여부, environment와 실제 시작/종료 시각을 `provenance.json`에 기록했습니다. 수정 중 실행한 검증이므로 base commit만으로 해당 실행 코드를 나타내지 않으며 실행 source hash를 함께 사용해야 합니다. console 로그와 실패 원인도 로컬에 보존했습니다.

## Conclusion and limits

로컬 학습·평가 pipeline은 동작했습니다. 32장 1-epoch는 과학적인 baseline·수렴 여부·model family 비교의 근거가 아닙니다. 일부 MPS 연산은 deterministic implementation이 없어 seed 고정 후에도 bitwise 재현을 보장하지 않습니다. 다음 실행은 전체 공식 train/val을 사용하는 1-epoch pilot으로 구분합니다. 공식 VisDrone evaluator와 ignore 영역 처리, 사람이 확인하는 failure 원인은 추가 검증 대상입니다.
