# VisDrone dataset preparation plan

문서 확인일: **2026-10-08 (Asia/Seoul)**. 상태: **준비 계획과 검증·시각화·YOLO 변환 도구 구성, 실제 데이터 미다운로드·미검증**. 실제 데이터 변환·학습·추론·benchmark는 실행하지 않았다. 도구는 합성 예제로만 검증했다.

## Target release and scope

프로젝트의 첫 데이터 준비 대상은 **VisDrone2019-DET (Task 1: Object Detection in Images)**로 정한다. VID/MOT/SOT 데이터를 섞지 않고, YOLO와 RT-DETR은 동일한 DET split을 사용하도록 계획한다. 공식 배포 목록에는 train, val, test-dev, test-challenge가 있으며 test-dev GT는 공개되고 test-challenge GT는 제공되지 않는다고 안내한다. [공식 배포 README](https://github.com/VisDrone/VisDrone-Dataset/blob/4364e8265275dfa44fd8f767b5180af58580194d/README.md)

공식 웹사이트의 2024-DET 안내는 데이터가 2019-DET와 같다고 설명한다. 이 프로젝트는 명칭을 `visdrone2019-det`로 통일하되, 실제 받은 archive의 이름·출처·hash를 별도로 기록한다. 연도 명칭만으로 파일 동일성을 검증했다고 주장하지 않는다. [공식 DET 다운로드 안내](https://aiskyeye.com/submit-2023/object-detection-2/)

## Split policy

| Split | 공식 문서 기재 이미지 수 | 프로젝트의 계획된 용도 |
| --- | --- | --- |
| train | 6,471 | 학습용 |
| val | 548 | 설정 비교, 모델 선택, 개발 중 failure analysis |
| test-dev | 1,610 | 설정을 고정한 뒤 최종 평가용; 초기 준비에서는 선택 사항 |
| test-challenge | 1,580 | 이번 로컬 baseline 범위에서 제외 |

train/val 수는 [공식 DET toolkit](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md), test 수는 [공식 test 안내](https://aiskyeye.com/evaluate/test-guidelines_2021/)를 따른다. 위 값은 **출처가 기재한 기대치이며 로컬 파일을 센 결과가 아니다**. 다운로드 후 실제 수와 일치 여부를 별도로 기록한다.

공식 test 안내는 test 데이터의 학습 사용을 금지하고 val에서 debugging할 것을 권한다. 프로젝트는 test-dev의 공개 label도 학습·튜닝에 사용하지 않는 정책을 적용한다. 해상도·tiling·augmentation 선택은 val에서 수행하고 최종 선택을 고정한 뒤 test-dev를 평가한다. 반복 평가로 선택이 바뀌면 그 사실을 기록한다. 공식 challenge 제출은 별도의 규칙 확인이 필요한 향후 작업이다. [공식 test 안내](https://aiskyeye.com/evaluate/test-guidelines_2021/)

## Use conditions and portfolio sharing

현재 공식 조건 페이지는 학술 이용, 출처 표시, 비상업 이용, 동일 조건의 파생물 공유를 안내하고 CC BY-NC-SA 3.0을 명시하지만, copyright 문구의 대상은 **VisDrone2021**이다. 이 정보만으로 2019 archive의 적용 조건을 확정하지 않는다. [공식 Privacy & Data Protection](https://aiskyeye.com/data-protection/)

데이터를 받을 때 해당 release의 README/license/배포 조건을 다시 확인하고 [기록 양식](dataset-record-template.md)에 근거와 확인 날짜를 남긴다. 2019에 적용되는 조건이 불명확하면 공식 설명이나 배포자 확인이 필요하다는 상태를 기록한다. 현재 release별 이용 조건 확인은 완료되지 않았다.

이 프로젝트의 공유 정책:

- raw images, videos, annotations, archives 및 변환 labels는 GitHub에 넣지 않는다.
- 결과 공개 시 공식 데이터셋 출처와 사용한 논문·toolkit을 인용한다.
- 포트폴리오 공개가 raw 이미지 재배포 허가를 뜻하지 않는다. 이미지·GIF 공유 조건이 확인되기 전에는 이미지 예시를 공개하지 않는다.
- class별 집계표·plot도 실제 데이터 확인 후 생성하고 공유 가능한 범위를 검토한다.
- 데이터셋 조건과 미래 model framework/code의 license를 구분해 기록한다.

## Planned local layout

아래는 프로젝트가 사용할 권장 구조이며 실제 archive 내부 구조를 확인한 결과가 아니다. 다운로드 승인 후 압축 내부 경로를 확인하고 원본 이름을 보존한다.

```text
data/visdrone/visdrone2019-det/
├── archives/                    # 공식 원본 압축파일과 SHA-256
├── raw/
│   ├── VisDrone2019-DET-train/
│   │   ├── images/
│   │   └── annotations/
│   ├── VisDrone2019-DET-val/
│   │   ├── images/
│   │   └── annotations/
│   └── VisDrone2019-DET-test-dev/ # 선택 사항; 도입 시 동일 구조 확인
├── derived/<conversion-version>/ # 향후 YOLO/COCO 변환 결과
└── metadata/
    ├── acquisition.md           # 출처, 적용 조건, archive hash
    ├── file-manifest.csv        # split, 상대 경로, 크기, SHA-256
    └── validation-report.json   # 실제 검사 결과와 제외/수정 내역
```

**현재 이 구조와 파일은 생성하지 않는다.** `data/`와 `datasets/` 전체는 `.gitignore` 대상이다. 세부 metadata도 기본적으로 로컬에 보관하고, 비밀정보·raw annotation이 없는 검토된 요약만 향후 `docs/datasets/<snapshot-id>/README.md`로 공유한다.

향후 실험 설정에서는 [설정 양식](../configs/experiment.example.toml)의 `dataset.release`, `root`, 각 split, manifest hash와 변환 버전을 채운다. 원본을 읽는 loader의 root는 `data/visdrone/visdrone2019-det/raw`로 계획하며, 변환본을 사용하면 해당 `derived/<conversion-version>` 경로를 명시한다. 현재 example의 빈 값은 유지한다.

## Annotation and planned class mapping

공식 DET annotation은 comma로 구분한 8개 필드의 TXT 형식이다. bbox는 원본 이미지의 좌상단 위치와 pixel 단위 폭·높이이고, GT의 score 0은 ignore, 1은 평가 대상이다. truncation과 occlusion도 제공된다. [공식 annotation 설명](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md)

```text
bbox_left,bbox_top,bbox_width,bbox_height,score,object_category,truncation,occlusion
```

[YOLO 변환 도구 v1](visdrone-yolo.md)에 구현하고 합성 예제로 검증한 10개 target class mapping (실제 데이터 미변환):

| 원본 ID | Class | 모델 ID (v1) |
| --- | --- | --- |
| 1 | pedestrian | 0 |
| 2 | people | 1 |
| 3 | bicycle | 2 |
| 4 | car | 3 |
| 5 | van | 4 |
| 6 | truck | 5 |
| 7 | tricycle | 6 |
| 8 | awning-tricycle | 7 |
| 9 | bus | 8 |
| 10 | motor | 9 |

원본 class 0은 ignored regions, 11은 others이다. 모델 ID는 프로젝트의 변환 정책이며 실제 VisDrone 변환은 아직 실행하지 않았다. 공식 evaluator는 ignored regions와 others 관련 검출을 제외하는 규칙을 갖는다. [공식 annotation·평가 설명](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md)

변환 v1 정책과 향후 평가 구현 시 검증할 규칙:

- 원본 score/ignore 영역/others와 truncation/occlusion을 보존한다. score 0 및 class 0/11을 일반 target class로 변환하지 않는다.
- label에서 ignore 항목만 삭제한 평가를 공식 VisDrone 평가와 동일하다고 주장하지 않는다. ignore 판정과 bbox 좌표 경계 convention은 toolkit code와 실제 sample로 검증한다.
- YOLO 변환은 bbox 중심·폭·높이를 이미지 크기로 정규화하고, COCO 변환은 명시적인 category mapping을 사용한다. YOLO와 RT-DETR에 같은 split과 제외 정책을 적용한다.
- 이미지 밖 bbox를 임의로 clip/delete하지 않는다. 원본 기준과 변환 목적을 확인하고 수정 여부·개수·근거를 기록한다.
- small/tiny 크기 분석에는 원본 bbox 면적을 보존하고 기준·좌표계를 [평가 정책](evaluation.md)에 명시한다.

## Acquisition and validation checklist (future work)

다음 항목은 실제 데이터 다운로드·변환 작업을 수행할 때 사용할 계획이다. 아직 실제 데이터로 실행하지 않았다.

1. 적용 조건과 실제 archive 링크를 확인하고 train/val 준비 범위, 저장 공간과 외부 보관 위치를 정한다. 공식 페이지에서 연결된 배포처를 사용한다.
2. 각 archive의 출처·파일명·받은 날짜·크기·SHA-256을 기록한다. 공식 checksum이 없으면 로컬 hash를 계산했다고 명시하고 공식 인증 값으로 표현하지 않는다.
3. 원본 archive를 보존한다. 압축의 무결성과 안전한 상대 경로를 확인한 뒤 raw 영역에 풀며 기존 파일을 덮어쓰지 않는다.
4. image/annotation 대응, 실제 파일 수, 이미지 decode 가능 여부, TXT의 필드 수·숫자·category·score·bbox 크기·경계를 검사한다. 이상 항목은 조용히 삭제하지 않고 보고한다.
5. 파일 hash로 split 간 완전 중복을 확인한다. 가능하면 근접 이미지/sequence 식별도 검토한다. hash 검사만으로 모든 scene leakage가 없다고 단정하지 않는다.
6. image/annotation별 manifest를 만들고 변환 전후 sample, class·ignore 처리와 수량 변화를 비교한다. test-challenge는 label이 있다고 가정하지 않는다.
7. 버전이 고정된 변환 코드와 command, seed가 필요한 과정, 실행 환경을 기록한다. raw 데이터는 보존한다.
8. 실제 검사 결과와 적용 조건 근거를 검토하고, 관련 설정을 채운 뒤에만 baseline 구현·실행 준비 완료로 표시한다.

[VisDrone validator](visdrone-validation.md)는 파일 대응·annotation 값과 선택적인 exact duplicate·이미지 decoding·bbox 경계 검사 일부를 구현했으며 합성 예제로 테스트했다. 실제 VisDrone의 hash 계산, 파일 수·class 통계·leakage 검사·sample 시각화와 label 변환은 모두 **미실행**이다. near-duplicate/scene leakage와 release·이용 조건 등 도구가 검사하지 않는 항목도 별도로 확인해야 한다. dataset 상태는 [기록 양식](dataset-record-template.md)으로 관리하며 모델 성능은 [실험 기록](../experiments/template.md)에만 실제 output 근거로 기록한다.

[YOLO 변환 도구](visdrone-yolo.md)는 target bbox를 strict하게 검사하고 모든 원본 행을 보존하는 변환 정책을 합성 데이터로 검증했다. 실제 데이터에 대한 위 미실행 상태는 유지한다.
