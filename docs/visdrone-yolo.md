# VisDrone → YOLO label conversion

현재 단계는 **합성 테스트와 실제 train/val 변환 v2·audit를 완료한 상태**이다. [실제 준비 기록](datasets/visdrone2019-det-2026-10-08/README.md)을 따른다. Trainer loading, 학습·추론·benchmark는 아직 실행하지 않았다. 변환 완료는 데이터 준비나 연구 결과의 완료를 의미하지 않는다. 기존 `Pillow==12.3.0`만 사용한다.

## Synthetic demo

[Setup](../README.md#setup) 후 저장소 root에서:

```bash
source .venv/bin/activate
python scripts/convert_visdrone_yolo.py --demo \
  --output-dir outputs/visdrone-yolo/synthetic-demo-v1
```

임시 train/val PNG/TXT를 생성하고 제거한다. output `manifest.json`에는 `source_kind: synthetic_demo`가 남는다. 매번 새로운 output directory를 지정한다. 이 데모는 작은 합성 label을 처리하는 소프트웨어 확인이며 성능 metric을 생성하지 않는다.

## Future prepared local data

**아래는 실제 train/val에서 실행한 v2 command이다. 기존 output이 있으면 새 경로를 지정한다.** 먼저 [dataset 준비 정책](dataset.md)에 따라 release·이용 조건과 split을 확인하고 [validator](visdrone-validation.md) 및 [preview](visdrone-preview.md)로 원본을 검토한다.

```bash
python scripts/convert_visdrone_yolo.py \
  --root data/visdrone/visdrone2019-det/raw \
  --splits train val --zero-area-policy exclude \
  --output-dir data/visdrone/visdrone2019-det/derived/visdrone-yolo-v2
```

train+val은 필수이며 labeled test-dev는 `--splits train val test-dev`로 선택할 수 있다. test-dev는 output의 `test`로 매핑하며 학습·튜닝에 사용하지 않는다. test-challenge는 지원하지 않는다. root 아래 공식 split directory와 직접 포함된 JPG/JPEG/PNG 및 TXT를 읽는다. stem은 대소문자를 구분해 일치해야 하고, 확장자·대소문자 충돌도 거부한다. 이미지와 annotation이 없는 split, missing pair는 오류이다.

## Conversion policy v2

[YOLO 형식](https://docs.ultralytics.com/datasets/detect/)에 따라 한 행은 `class x_center y_center width height`이다. 원본 좌표 `(x, y, w, h)`와 이미지 크기 `(W, H)`에서 `(x+w/2)/W`, `(y+h/2)/H`, `w/W`, `h/H`로 변환한다. [원본 class](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md) 1–10 → 모델 ID 0–9이며 이름과 순서는 [class mapping 표](dataset.md#annotation-and-planned-class-mapping)를 따른다.

- score 1/category 1–10만 target label로 쓴다. score 0 또는 category 0은 ignored, 나머지 category 11은 other로 분류해 label에서 제외한다. 모든 유효 행의 원본 8개 값·line number·kind와 변환 값을 JSONL에 보존한다.
- **행 제외는 학습 loss의 ignore mask가 아니다.** 이미지 픽셀은 그대로 남는다. 제외 영역의 객체가 background로 취급될 가능성이 있으며, 빈 target label 이미지도 자동으로 삭제하지 않는다. 이 정책의 영향을 baseline 설계 때 검토한다. JSONL의 ignore 정보는 일반 YOLO loader가 자동으로 사용하지 않는다.
- label에서 ignore/other 행을 제거한 YOLO 평가를 공식 VisDrone 평가와 동일하다고 주장하지 않는다. 원본 ignore 영역을 사용한 evaluator 연결은 향후 별도 구현·검증한다. [공식 toolkit 평가 설명](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md)
- bbox는 raw pixel 좌표이다. resize·clipping·masking하지 않는다. target이 이미지 밖에 있으면 오류로 중단한다. ignored/other bbox는 변환하지 않으므로 화면 밖 좌표도 원본 값으로 보존한다.
- 기존 [공통 GT parser](../src/uav_small_target/visdrone_annotations.py)를 사용한다. 잘못된 행은 ignored/other라도 기본적으로 오류이다. v2의 `--zero-area-policy exclude`를 명시하면 0면적 행만 제외하고 모든 원본 값·line·사유를 보존한다. 음수 폭/높이와 그 외 오류는 계속 중단한다. 기본값 `reject`와 validator/preview는 기존 strict 동작을 유지한다. unusual truncation/occlusion 값은 보존하고 경고로 기록한다.
- JPEG/PNG verify 후 재열기·load하며 손상·multi-frame·Pillow 픽셀 제한 오류·UTF-8 오류는 중단한다. 이미지 bytes를 그대로 복사한다. 원본이 이동·수정되지 않는다. EXIF orientation이 1 이외인 이미지는 trainer가 회전할 때 label 불일치가 생길 수 있어 명시적인 좌표 정책이 생길 때까지 거부한다.
- 소수 bbox를 정수로 반올림하지 않는다. Python float 결과를 17 significant digits로 쓴다. 양수 폭/높이의 float extent가 사라지거나 정규화 후 0이 되면 거부한다. 임의의 실수에 대한 무한 정밀도를 보장하지는 않는다.

## Output and provenance

```text
<new-output>/
├── images/{train,val[,test]}/ # 원본 bytes 복사
├── labels/{train,val[,test]}/ # 같은 stem의 YOLO TXT; 빈 target은 빈 TXT
├── dataset.yaml              # 10개 names, split 경로; download hook 없음
├── annotations.jsonl         # pair별 원본 행, 입력 SHA-256, label SHA-256, 경고
└── manifest.json             # 변환 버전, 정책, 환경, class/split mapping, 처리 수량
```

`dataset.yaml`의 `path`는 output의 실제 절대 경로이다. output을 다른 컴퓨터로 옮기면 이 경로를 수정하고 변경 이력을 기록해야 한다. YAML 구조는 테스트에서 확인했고 합성 데모 산출물은 로컬 Ruby Psych로 실제 parsing을 확인했다. Ruby는 프로젝트 dependency나 CI 요구사항이 아니다. Ultralytics loading은 미검증이며 관련 패키지를 설치하지 않았다. YAML에 training command나 자동 다운로드 코드는 넣지 않는다.

manifest의 수량은 변환한 input의 처리 내역이며 모델 metric이 아니다. JSONL·YAML hash도 기록한다. pair 단위로 입력을 읽어 동일 bytes를 decoding·hash·복사에 사용하고, JSONL을 순서대로 쓴다. 시간·임시 raw 절대 경로는 기록하지 않는다. 동일 입력에서 label과 JSONL은 결정적으로 생성되지만 YAML/manifest는 output 절대 경로와 실행 환경에 따라 달라진다. 실행 command·Git commit·release/archives hash는 [데이터 준비 기록](dataset-record-template.md)에 별도로 남긴다. 변환 버전은 `visdrone-yolo-v2` (v1은 0면적 제외 옵션 없음)이며 앞으로 정책 변경 시 버전을 갱신한다.

raw와 output은 서로 포함되지 않는 경로여야 하며 symlink도 실제 경로로 확인한다. 기존 output은 비어 있어도 거부한다. 임시 staging에서 변환을 마친 뒤 새 output을 독점 생성하고 파일을 옮긴다. 입력 오류는 staging만 정리하고 output을 공개하지 않는다. **최종 파일 이동은 여러 단계여서 atomic publication은 아니다.** I/O 오류·중단이 발생하면 새 output이나 숨겨진 `.uav-convert-*` staging이 남을 수 있다. exit code와 산출물·hash를 확인하고 새 경로에서 재실행한다. 기존 파일을 자동 삭제하지 않는다.

CLI stdout은 manifest JSON, stderr는 결과·오류 안내이다. exit 0은 변환 완료(경고는 manifest/JSONL 확인), exit 2는 인자·dependency·입력·저장 오류이다. 실제 변환본·원본 annotation·manifest는 로컬 `data/` 또는 `outputs/`에 두고 commit하지 않는다.

## Validation and remaining work

```bash
python -B -m unittest discover -s tests -v
python -B scripts/validate_structure.py
```

[합성 테스트](../tests/test_visdrone_yolo.py)는 class/ignore 보존, 좌표 round-trip·정밀도·경계, 입력/output hash·원본 보호·반복성, 빈 label, 오류 뒤 미공개, decoding/EXIF, split/YAML 구조, 경로·충돌·overwrite 및 CLI를 확인한다. 실제 release·조건, exact duplicate/scene leakage, trainer loading/ignore loss 처리, 공식 evaluator·모델 성능은 미검증이다. 이 항목들은 다음 데이터 준비·baseline·평가 단계에서 별도로 검증한다.
