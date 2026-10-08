# exp-003 — YOLO11n 50-epoch MPS baseline

**Status: prepared / final results pending. 아직 본학습 최종 결과가 없습니다.** 실제 실행 상태는 로컬 `outputs/.jobs/exp-003-yolo11n-baseline-mps/job.json` 및 `outputs/exp-003-yolo11n-baseline-mps/progress.json`에서 확인합니다. 완료된 run의 최종 결과만 이 문서와 summary에 추가합니다.

## Hypothesis and fixed conditions

YOLO11n을 전체 VisDrone train/val로 50 epochs fine-tuning하여 입력 해상도·tiling·augmentation 비교의 기준을 확보합니다. 본학습 종료는 수렴의 자동 증명이 아니며 loss/val curve와 best epoch를 함께 검토합니다.

- [설정](../../configs/yolo-baseline-mps.toml): imgsz 640, batch 8, MPS FP32, seed 42, 50 epochs
- 동일 COCO-pretrained YOLO11n·weights hash, 동일 변환 v2·dataset manifest hash
- Train 6,471 / val 548장; SGD lr0 0.01, momentum 0.937, weight_decay 0.0005, mosaic 1.0
- 마지막 10 epochs에서 mosaic 종료. effective warm-up은 설치된 framework의 3 epochs이며 1-epoch pilot의 effective warm-up 0과 다름
- evaluator/confidence/NMS/maxDet/area/timing은 [pilot](../exp-002-yolo11n-pilot-mps/README.md)과 동일. epoch 수·LR schedule·mosaic 종료 정책이 달라 pure epoch-only ablation으로 해석하지 않음
- 공식 VisDrone ignore masking 미적용, train 중복 label 처리와 MPS 결정성 한계 유지

## Execution

검증한 code/config를 commit한 뒤 저장소 root에서 실행합니다:

```bash
.venv-yolo/bin/python -B scripts/start_yolo_job.py --config configs/yolo-baseline-mps.toml --export
.venv-yolo/bin/python -B scripts/start_yolo_job.py --status exp-003-yolo11n-baseline-mps
```

별도 로컬 process가 학습 → 최종 validation → 전체 prediction/COCO 평가 → 고정 P/R·timing을 수행합니다. `console.log`, job 상태, config snapshot을 ignored `outputs/.jobs/<id>/`에 보존하며 epoch 완료 후 `progress.json`을 atomic하게 갱신합니다. 50/50 epochs에 도달해도 후속 평가가 끝나기 전에는 completed로 표시하지 않습니다. 실제 종료 epoch가 요청한 50과 다르면 runner는 실패로 기록합니다.

성공 후 checkout branch·HEAD가 동일하고 사용자 변경사항이 없으면 검토용 summary/CSV/AP plot만 working directory에 생성합니다. 기존 README는 유지합니다. checkout이 바뀌면 결과는 로컬에 남기고 `completed_awaiting_export`로 기록합니다. worker는 commit/push/merge를 수행하지 않습니다. 결과 검토 후 별도 commit·push·PR review로 마무리합니다.

Mac에서는 job 수명 동안 `caffeinate -i -s`로 idle sleep을 방지합니다. 실행 종료 시 자동 해제되며 영구적인 OS 설정 변경은 없습니다. 장시간 학습 중에는 전원을 연결하고 덮개를 열어 둡니다. 재부팅·강제 종료·덮개 닫기로 중단되면 자동 재시작하지 않으며 checkpoint와 실패 로그를 보존합니다. 현재 runner의 checkpoint resume은 미구현이므로 중단 시 재개 경로를 검토한 뒤 진행합니다.

## Metrics, failure cases and conclusion

**not measured** — 50-epoch 결과·AP_small·P/R·FPS·latency와 수렴/failure 분석은 최종 output을 실제 확인한 뒤 기록합니다. pilot 수치를 본학습 결과로 복사하지 않습니다. 실제 GT/prediction overlay·weights·dataset은 공개하지 않습니다.
