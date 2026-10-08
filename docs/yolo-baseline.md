# YOLO11n baseline

YOLO11n의 작은 variant로 학습·평가의 첫 기준을 만듭니다. 모델 규모를 고정한 뒤 해상도·tiling·augmentation을 비교합니다. [공식 YOLO11 문서](https://docs.ultralytics.com/models/yolo11/), [train API](https://docs.ultralytics.com/modes/train/), [validation API](https://docs.ultralytics.com/modes/val/)를 따릅니다.

## Environment and model

Python 3.11, `requirements-yolo.txt`의 Ultralytics 8.4.174 / PyTorch 2.14.1 / torchvision 0.29.1 / pycocotools 2.0.11을 사용합니다. 가벼운 데이터 도구의 `requirements.txt`와 구분합니다. 현재 로컬 호스트는 macOS 14.7.8 / Apple M1 / 16 GiB RAM이며 MPS를 사용합니다. CUDA 환경은 별도 검증 대상입니다. [PyTorch MPS 문서](https://docs.pytorch.org/docs/stable/notes/mps.html)를 참고하세요.

```bash
python3.11 -m venv .venv-yolo
.venv-yolo/bin/python -m pip install -r requirements-yolo.txt
.venv-yolo/bin/python -m pip check
mkdir -p weights
curl --fail --location https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt -o weights/yolo11n.pt
```

이미 weights가 있다면 다시 다운로드하여 덮어쓰지 마세요. 공식 release의 COCO-pretrained `yolo11n.pt` SHA-256은 `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`입니다. runner는 로컬 fingerprint를 대조하며 자동 다운로드하지 않습니다. 이 hash는 내려받은 파일의 fingerprint이며 별도의 공식 인증 hash와 대조한 것은 아닙니다. Ultralytics는 [AGPL-3.0 / Enterprise license](https://github.com/ultralytics/ultralytics/blob/main/LICENSE)를 제공합니다. 연구 코드는 모델 패키지 소스를 복사하지 않으며 향후 배포 시 이용 조건을 확인합니다.

## Three distinct runs

| Configuration | Purpose | Train/val | Epochs | Input | Device |
| --- | --- | --- | --- | --- | --- |
| [yolo-smoke.toml](../configs/yolo-smoke.toml) | 실행 경로 확인; 연구 baseline 아님 | seed 42로 32 / 8장 추출 | 1 | 320 | MPS |
| [yolo-pilot.toml](../configs/yolo-pilot.toml) | 전체 split의 예비 기준; 수렴 판정 불가 | 6,471 / 548장 | 1 | 640 | MPS |
| [yolo-baseline.toml](../configs/yolo-baseline.toml) | 본학습 계획 | 전체 split | 50 | 640 | CUDA 0, batch 16 |

```bash
.venv-yolo/bin/python -B scripts/run_yolo_experiment.py --config configs/yolo-smoke.toml --dry-run
.venv-yolo/bin/python -B scripts/run_yolo_experiment.py --config configs/yolo-smoke.toml
.venv-yolo/bin/python -B scripts/run_yolo_experiment.py --config configs/yolo-pilot.toml
# CUDA 장치가 있는 환경에서 데이터·weights와 경로를 준비한 뒤 실행:
.venv-yolo/bin/python -B scripts/run_yolo_experiment.py --config configs/yolo-baseline.toml
```

`--dry-run`은 TOML parsing만 수행하며 파일 생성·모델 import·데이터 검증을 하지 않습니다. 실제 실행은 고정 dependency, dataset manifest·annotation sidecar·선택 이미지/label hash와 weights를 대조합니다. train/val pair를 `outputs/<id>/dataset/`에 복사하고 framework cache를 그 안에 둡니다. 데이터 준비본과 원본은 변경하지 않습니다. smoke만 subset이 허용되며 pilot/baseline에는 전체 split이 필수입니다. seed에 따른 선택 목록은 `split-selection.json`에 보존합니다.

실행은 새 experiment ID만 허용합니다. 실패·중단한 폴더를 덮어쓰지 않습니다. 재시도할 때 ID가 다른 설정 파일을 만들고 원래 기록을 보존하세요. checkpoint resume 기능은 이번 runner에 없습니다. 시작 후 실패하면 `provenance.json`에 failed/interrupted 및 예외를 기록합니다.

## Recorded outputs

- `config.toml`, `provenance.json`: 실행 명령, Git commit/dirty 여부, 실행 source hash, 설정·dataset·weights hash, 시작·종료 시각
- `environment.json`: Python·모든 설치 package 버전, 실제 device, CUDA/MPS availability
- `train/args.yaml`, `train/results.csv`, `train/weights/`: framework의 실제 설정·epoch 로그·best/last checkpoint
- `ultralytics-validation.json`: framework metric과 class별 AP
- `coco-ground-truth.json`, `predictions.json`: 원본 픽셀 좌표 target 및 prediction
- `metrics.json`, `failure-analysis.json`: 별도 COCO AP, 고정 confidence의 P/R·오류 집계, 동기화 timing

모두 ignored `outputs/`에 있습니다. 설정을 바꾼 run은 새 ID로 기록하며 검토한 aggregate만 `experiments/` 및 `results/tables/`에 공개합니다. 실제 source와 설정 hash를 기록하므로 dirty working tree에서 한 검증도 추적할 수 있습니다. 환경 snapshot에는 인증정보나 private package URL을 수집하지 않습니다. 로컬 framework settings는 공개하지 않습니다.

## Evaluation protocol

seed 42와 `deterministic=True`를 기록하지만 PyTorch가 MPS의 `scatter_reduce`와 `index_put_with_accumulate`에 결정적 구현이 없다고 경고했습니다. bitwise 동일 결과를 보장하지 않습니다. pilot의 초기 1 epoch는 기본 `warmup_epochs=3` 구간에 포함되므로 수렴한 baseline으로 해석하지 않습니다. framework는 train 중복 label 4개를 로딩 시 제거했습니다(343,204 → 343,200 target). val 38,759 target은 동일합니다. 원본 및 변환 label 파일은 변경하지 않습니다.

**공식 VisDrone evaluator 결과가 아닙니다.** 변환 v2의 score=1, category 1..10 target만 사용하며 0면적 bbox는 제외합니다. ignored/other 영역은 loss mask나 평가 ignore 영역으로 적용되지 않습니다. 따라서 해당 영역의 prediction이 배경 false positive로 처리될 수 있습니다. 이 정책은 향후 RT-DETR 비교에도 같게 적용해야 합니다.

- AP prediction: confidence ≥ 0.001, class-aware NMS IoU 0.7, max_det 500. 별도 `pycocotools.COCOeval` bbox의 10 IoU threshold 0.50:0.05:0.95, 101 recall points, maxDets [1,10,500]를 사용합니다. 이 maxDet은 COCO 기본 100과 다릅니다. class/area에 GT가 없으면 제외하며 전부 없으면 `null`(미측정/해당 없음)입니다.
- `AP_small`: COCO small area range 0..1,024 px², **원본 image 좌표계** 기준입니다. IoU 0.50:0.05:0.95의 AP입니다. resize 후 bbox 면적이 아닙니다. COCO 구간 경계 1,024가 small/medium에 겹치는 기본 정의를 유지합니다.
- 고정 operating point Precision/Recall: confidence ≥ 0.25, 같은 class의 IoU ≥ 0.50, score 순 greedy one-to-one matching, 전체 image의 TP/FP/FN 합계로 계산합니다. prediction이 없으면 Precision은 null이며 GT가 있으면 Recall은 0입니다. 별도로 저장하는 Ultralytics P/R는 smoothed mean-F1-selected confidence 기준이며 동일 지표로 섞지 않습니다.
- timing: FP32, batch 1, confidence 0.25, NMS IoU 0.7, max_det 500. 선택 val의 사전 decoding된 BGR array를 사용하고 warm-up 3회 후 처음 최대 20장을 측정합니다(smoke 8장). MPS/CUDA는 호출 전후 동기화합니다. preprocessing + inference + NMS + result 구성은 포함하고 파일 I/O·JPEG decoding은 제외합니다. FPS는 이미지 수 / 총 측정 시간이며 평균·p50·p95 latency를 함께 기록합니다. 작은 sample이므로 장시간 처리속도 benchmark로 해석하지 않습니다.
- failure analysis: 같은 고정 operating point의 FN/FP 및 원본 면적 small FN을 집계하고 worst-case image ID를 보존합니다. 가림·밀집·해상도 등 원인 판정은 사람이 실제 이미지를 검토한 뒤 별도 기록합니다.

## Export a reviewed aggregate

```bash
.venv-yolo/bin/python -B scripts/summarize_yolo_run.py --run outputs/exp-002-yolo11n-pilot-mps --figure
```

완료된 run만 `experiments/<id>/summary.json`, `results/tables/<id>.csv`, 선택적인 면적별 AP plot으로 변환합니다. 원본 이미지·GT/prediction 전체·weights·절대 실행 경로·framework settings는 공개 요약에 복사하지 않습니다. 생성 후 diff와 수치·artifact hash를 검토하고 가설·분석·한계를 `experiments/<id>/README.md`에 추가합니다. 이미 생성한 공개 파일은 CLI로 덮어쓰지 않습니다. aggregate exporter의 write 중 오류가 나면 새 산출물이 일부 남을 수 있으므로 검토합니다.

원본의 split 내부 중복은 공식 구성을 보존합니다. near-duplicate/scene leakage와 2019 release별 license 적용은 [데이터 준비 기록](datasets/visdrone2019-det-2026-10-08/README.md)의 한계를 유지합니다. 본학습 전에 label 표현 정책·평가 정의를 고정하고 convergence와 loss curve를 검토합니다.
