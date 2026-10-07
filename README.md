# 01-UAV-Small-Target-Detection

UAV 항공영상의 tiny/small object detection 성능을 분석하고 개선하는 연구 및 취업 포트폴리오 프로젝트입니다.

**현재 단계: 프로젝트 기반 구조 구축. 학습·추론·benchmark를 실행하지 않았으며 측정 결과는 없습니다.** 아래 모델과 실험은 계획입니다.

## Project overview

VisDrone 기반 YOLO 및 RT-DETR baseline에서 시작해 객체 크기별 성능, 입력 해상도, tiled inference와 augmentation의 효과를 비교합니다. 각 실험은 **가설 → 구현 → 측정 → 결과 분석 → failure analysis**를 남깁니다.

## Research motivation

항공영상의 작은 객체는 제한된 픽셀 수, 밀집도, 가림과 배경 때문에 검출이 어려울 수 있습니다. 전체 mAP뿐 아니라 작은 객체의 오류와 정확도·처리속도 사이의 관계를 확인하고, 재현 가능한 근거로 개선 방향을 찾습니다.

## Research questions

- YOLO와 RT-DETR은 동일 평가 조건에서 tiny/small 객체를 어떻게 검출하는가?
- 입력 해상도를 높이면 크기별 정확도와 latency가 어떻게 변하는가?
- tiled inference는 작은 객체의 Recall에 어떤 영향을 주며 비용과 중복 검출은 어떠한가?
- augmentation 변경은 어떤 failure case를 줄이거나 늘리는가?

## Planned models

| Model family | Planned role | Status |
| --- | --- | --- |
| YOLO | 최초 baseline 및 해상도·tiling·augmentation 비교 | 미구현 |
| RT-DETR | 다른 검출 구조의 baseline 비교 | 미구현 |

세부 model variant, 구현체, pretrained weights 및 버전은 도입 시 선정·기록합니다. 현재 확정한 framework dependency는 없습니다.

## Dataset

계획한 데이터셋은 **VisDrone**입니다. dataset 자체는 repository에 포함하지 않습니다. 정확한 release, split, annotation 변환 규칙과 이용 조건은 데이터 준비 단계에서 확인합니다.

- 권장 로컬 위치: `data/visdrone/<release>/`
- `data/`, `datasets/`는 `.gitignore`로 제외하며 현재 생성·다운로드하지 않습니다.
- version, checksum, class mapping, split과 변환 이력은 [dataset 관리 정책](docs/dataset.md)에 따라 기록합니다.

## Evaluation metrics

계획한 metric은 `mAP50`, `mAP50-95`, `AP_small`, `Precision`, `Recall`, `FPS`, `latency`입니다. [평가 정책](docs/evaluation.md)에 evaluator, 객체 면적 기준과 timing 조건을 기록합니다. tiny/small 크기 구간과 `AP_small` 정의는 실제 evaluator 도입 전에 확정합니다.

## Planned experiments

| Experiment | Hypothesis / comparison | Status |
| --- | --- | --- |
| YOLO baseline | 첫 기준 성능과 failure 유형 확보 | 계획 |
| RT-DETR baseline | 동일 dataset/evaluator 조건에서 검출 구조 비교 | 계획 |
| Input resolution | 더 높은 해상도가 small-object 정확도와 처리 시간에 미치는 영향 | 계획 |
| Tiled inference | tile 크기·overlap·merge 정책에 따른 Recall과 latency 비교 | 계획 |
| Augmentation | 동일 조건에서 augmentation 변경과 오류 유형 비교 | 계획 |
| Failure analysis | 크기·가림·밀집도별 miss, false positive, localization 분석 | 계획 |

## Repository structure

```text
01-UAV-Small-Target-Detection/
├── AGENTS.md                 # Codex 운영 및 연구·Git 규칙
├── README.md
├── .gitignore
├── requirements.txt          # 현재 주석만 포함
├── configs/
│   ├── README.md
│   └── experiment.example.toml
├── src/README.md             # 향후 구현 공간
├── scripts/
│   ├── README.md
│   └── validate_structure.py
├── notebooks/README.md
├── experiments/
│   ├── README.md
│   └── template.md           # 미실행 실험 기록 양식
├── results/
│   ├── README.md
│   ├── figures/README.md
│   └── tables/README.md
├── docs/
│   ├── README.md
│   ├── dataset.md
│   ├── dependencies.md
│   ├── evaluation.md
│   └── git-workflow.md
└── assets/README.md
```

각 directory의 `README.md`가 목적 설명과 빈 directory 유지 역할을 합니다. 로컬 전용 `data/`, `weights/`, `outputs/`는 위 tracked 구조에 포함되지 않습니다.

## Setup

초기 기준은 **Python 3.11**입니다. 설치된 Python으로 표준 라이브러리 기반 검증을 실행할 수 있으며, model framework 호환성은 향후 확인합니다. [Dependency 전략](docs/dependencies.md)을 참고하세요.

새 컴퓨터에서 준비하는 예시:

```bash
git clone https://github.com/yejunhui811/01-UAV-Small-Target-Detection.git
cd 01-UAV-Small-Target-Detection
git switch main
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_structure.py
```

`requirements.txt`는 현재 주석만 있어 모델 패키지를 설치하지 않습니다. 가상환경 없이도 Python 3.11에서 `python3 scripts/validate_structure.py`로 구조를 검증할 수 있습니다. 이 단계에 실행할 학습·추론 명령은 없습니다.

## Reproducibility policy

- [실험 기록 안내](experiments/README.md)와 [기록 양식](experiments/template.md)을 사용합니다.
- experiment ID, hypothesis, model/dataset version, 설정, command, seed, code commit, 환경을 기록합니다.
- [TOML 설정 양식](configs/experiment.example.toml)의 빈 값은 미정 항목입니다. 실행 가능한 모델 설정이 아닙니다.
- 원본 output과 검토된 metric을 연결하고 실패·미측정 결과를 명확히 표시합니다.
- 데이터, weights, cache와 대용량 output은 Git에 넣지 않습니다. 작은 검토된 표·figure만 공유합니다.
- 실제 output으로 확인하지 않은 수치는 README에 작성하지 않습니다.

## Results and visualizations

**아직 실험 결과, 성능 표, figure/GIF가 없습니다.** 실제 측정 후 [결과 안내](results/README.md)에 따라 [tables](results/tables/), [figures](results/figures/)와 experiment 기록을 연결하고 이 절에 추가합니다.

## Roadmap

- [x] 기반 구조 검토 및 사용자 승인 후 main에 반영 ([PR #1](https://github.com/yejunhui811/01-UAV-Small-Target-Detection/pull/1))
- [ ] VisDrone version/split·이용 조건 확인 및 로컬 데이터 관리
- [ ] YOLO baseline 구현 및 검증
- [ ] RT-DETR baseline 구현 및 검증
- [ ] 크기별 evaluation 정의 및 failure analysis
- [ ] 입력 해상도 비교
- [ ] Tiled inference 비교
- [ ] Augmentation 비교
- [ ] 실제 결과·figure와 재현 명령을 정리한 포트폴리오

## Git/GitHub workflow

최신 `main`에서 별도 branch를 만들고 변경 → 검증 → `git add` → commit → push → Pull Request 검토 → 사용자 승인 후 merge 순서로 진행합니다. PR 생성과 push만으로는 `main`에 반영되지 않습니다. `main` merge에는 사용자의 명시적 허가가 필요합니다. merge 후에는 로컬 `main`을 동기화하고 다음 작업 branch를 만듭니다. 명령의 의미와 이후 흐름은 [Git 안내](docs/git-workflow.md), 프로젝트 운영 규칙은 [AGENTS.md](AGENTS.md)를 참고하세요.
