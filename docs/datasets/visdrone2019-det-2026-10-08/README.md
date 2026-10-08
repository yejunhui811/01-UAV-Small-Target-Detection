# VisDrone2019-DET local preparation: 2026-10-08

**Status: prepared with documented exceptions.** 사용자가 실제 데이터 다운로드·준비를 허용한 뒤 공식 Google Drive train/val을 받아 검사하고 YOLO 변환을 완료했다. test-dev/test-challenge는 받지 않았다. 학습·추론·benchmark는 아직 실행하지 않았으며 모델 성능 수치는 없다. 아래는 실제 데이터 처리 수량이다. 기계 판독 근거와 실행 source fingerprint는 [summary.json](summary.json)에 있다.

다운로드는 2026-10-08에 완료했고, 준비 기록 마감일은 2026-10-09 (Asia/Seoul)이다. Snapshot ID는 다운로드 날짜를 유지한다.

## Acquisition and terms

출처는 [공식 VisDrone README](https://github.com/VisDrone/VisDrone-Dataset)의 [train Google Drive](https://drive.google.com/file/d/1a2oHjcEcwXP8oUF95qiwrqzACb2YlUhn/view?usp=sharing), [val Google Drive](https://drive.google.com/file/d/1bxK5zgLn0_L8x276eKkuYA_FzwCIjb59/view?usp=sharing) 링크이다. Ultralytics mirror는 크기 참고만 했으며 실제 다운로드는 공식 Drive에서 HTTP 200으로 완료했다. 확인일은 2026-10-08 Asia/Seoul이다.

| Archive | 수신 크기 bytes | 로컬 계산 SHA-256 |
| --- | ---: | --- |
| VisDrone2019-DET-train.zip | 1549875511 | `86a77eba93137bfc16e4993860de9245b0675c0dba0d3ab98fb458699e256f84` |
| VisDrone2019-DET-val.zip | 81638851 | `abeea063037e5d20398837deb11084e652402a34ddf4f207bdf541a6f2a35ef9` |

전체 ZIP CRC와 파일 크기는 통과했고 모든 추출 파일의 hash를 기록했다. 공식 인증 SHA-256은 확인하지 못했으므로 위 값은 다운로드한 bytes의 fingerprint이며 공식 checksum 일치나 release 진위 검증을 뜻하지 않는다. val ZIP의 `.DS_Store` 1개도 보존·기록했다. raw 파일 합계는 14,039개이다.

[현재 공식 조건](https://aiskyeye.com/data-protection/)의 학술 이용 안내는 확인했다. 페이지의 CC BY-NC-SA 3.0 copyright 대상은 VisDrone2021이고 실제 ZIP에는 LICENSE/README가 없어서 **2019 release별 정확한 license 적용은 unresolved**로 기록한다. [현재 DET 안내](https://aiskyeye.com/submit-2023/object-detection-2/)는 2024 데이터가 2019와 같고 다운로드·이용할 수 있다고 설명한다. 이 근거로 로컬 학술·비상업 연구 준비를 진행했으며 raw images/annotations/derived labels/preview는 공개하지 않는다. 이미지·GIF 공개나 상업 이용 전 release별 조건 확인이 필요하다.

Citation: Zhu et al., *Detection and Tracking Meet Drones Challenge*, IEEE TPAMI, 44(11), 7380–7399, DOI `10.1109/TPAMI.2021.3119563`. [공식 데이터셋 인용 안내](https://github.com/VisDrone/VisDrone-Dataset#citation)

## Actual validation and conversion

| 항목 | Train | Val |
| --- | ---: | ---: |
| 이미지 / matching TXT | 6471 / 6471 | 548 / 548 |
| 정상 decoding 이미지 | 6471 | 548 |
| 원본 nonblank annotation 행 | 353550 | 40169 |
| 변환 target label 행 | 343204 | 38759 |
| 0면적을 제외한 ignored/other 제외 행 | 10343 | 1410 |
| 0면적 제외 행 | 3 | 0 |
| 빈 target label 이미지 | 0 | 0 |
| split 내부 완전 중복 발견 건수 | 2 | 1 |

공식 train/val 이미지 기대 수량과 일치한다. missing pair·손상 decoding·유효 bbox의 경계 초과·train–val exact duplicate는 발견되지 않았다. **Near-duplicate/scene leakage는 검사하지 않았다.** 동일 split의 완전 중복 이미지는 공식 파일 목록을 유지하기 위해 삭제하지 않았다.

원본 strict validator는 `failed`, error 3개·warning 3개를 보고했다. error는 모두 height 0인 train annotation으로 ignored 2행과 car target 1행이다. 원본은 수정하지 않았다. 기본 strict 변환 v1도 이 오류에서 exit 2로 중단했고 완성 output을 만들지 않았다.

변환 v2에 `--zero-area-policy exclude`를 명시해 **0면적 행 3개만** 제외했다. 원본 모든 행의 값·line number·hash와 제외 사유는 로컬 `annotations.jsonl`에 남겼다. 음수 bbox·범위 밖 target·그 외 잘못된 annotation을 허용하는 정책은 아니다. ignored/other 11,753행도 YOLO label에서 제외했으나 원본 정보는 보존했다. YOLO target 합계는 381,963행, 이미지/label pair는 7,019개이다. 원본 검사 결과를 passed로 바꾸지 않는다.

변환 상태는 `converted_with_warnings`이다. warnings는 원본에서 찾은 3건 중복과 별개로, 변환기의 0면적 제외 및 ignored 영역이 일반 trainer loss에서 자동으로 무시되지 않는다는 안내를 기록한다. 정확한 범위는 [변환 정책](../../visdrone-yolo.md)을 따른다.

## Audit and samples

- 원본 14,039개 파일의 inventory·size·SHA-256을 extraction manifest와 재대조해 변경 없음 확인.
- 모든 변환 이미지 bytes와 입력 image hash, label hash, JSONL/YAML artifact hash 대조 통과.
- 모든 target label의 class·정규화 범위와 pixel xywh 역변환 대조 통과. 좌표 tolerance는 absolute `1e-9` pixels / relative `1e-12`이다.
- train/val 각각 파일명 순 첫 pair의 GT preview를 생성하고 눈으로 bbox와 원본 이미지를 검토했다. 전체 이미지 내용이나 모든 bbox 의미를 사람이 검토했다는 뜻은 아니다. preview와 원본은 로컬에만 보관한다.
- 실제 변환 `dataset.yaml`을 Ruby Psych로 parsing 확인. Ultralytics loader는 아직 설치·실행하지 않았다.

## Reproduction and local artifacts

로컬 root는 `data/visdrone/visdrone2019-det/`이다. `archives/`, `raw/`, `metadata/`, `derived/visdrone-yolo-v2/` 모두 ignored이다. Detailed source rows, file manifest, validation report, duplicate/exception 목록과 preview는 GitHub에 포함하지 않는다. 공유한 파일은 이 요약과 hash·집계 정보뿐이다.

```bash
python -B scripts/extract_visdrone.py \
  --archive-dir data/visdrone/visdrone2019-det/archives \
  --raw-root data/visdrone/visdrone2019-det/raw \
  --metadata-dir data/visdrone/visdrone2019-det/metadata/extraction-v1
python -B scripts/validate_visdrone.py \
  --root data/visdrone/visdrone2019-det/raw --splits train val \
  --check-images --check-duplicates \
  --report data/visdrone/visdrone2019-det/metadata/validation-v1.json
python -B scripts/convert_visdrone_yolo.py \
  --root data/visdrone/visdrone2019-det/raw --splits train val \
  --zero-area-policy exclude \
  --output-dir data/visdrone/visdrone2019-det/derived/visdrone-yolo-v2
python -B scripts/audit_visdrone_preparation.py \
  --raw-root data/visdrone/visdrone2019-det/raw \
  --derived-root data/visdrone/visdrone2019-det/derived/visdrone-yolo-v2 \
  --file-manifest data/visdrone/visdrone2019-det/metadata/extraction-v1/file-manifest.jsonl \
  --report data/visdrone/visdrone2019-det/metadata/audit-v2.json
```

실행 때 `.venv/bin/python -B`를 사용했다. 환경은 Python 3.11.9 / Pillow 12.3.0 / macOS arm64이다. seed를 사용하는 작업은 없었다. 이미 존재하는 raw/output/report는 보호되므로 재실행 시 새 위치/version을 지정한다. 다운로드 command와 extraction 제한은 [준비 안내](../../visdrone-extraction.md)를 따른다.

Raw validation은 base commit `df0441848b8101d2cb96ccbf81e3bc3c47eeb298`의 strict 동작으로 실행했다. Extraction·변환 v2·audit는 이 branch의 새 코드로 실행했으며 [summary.json](summary.json)의 `executed_source_sha256`으로 실행 파일을 식별한다. 완성 commit은 이 snapshot을 추가한 Git 이력으로 확인하고 로컬 provenance에도 기록한다. YAML의 절대 경로가 달라지면 해당 artifact hash도 달라진다.

## Readiness

**1단계의 로컬 다운로드·검증·예외 기록·변환·audit는 완료했다.** 다음 baseline 구현에 사용할 수 있다. 학습 전 trainer loading·ignore loss 처리와 장치/모델 환경을 검증해야 한다. 공식 evaluator 동등성, near-duplicate/scene leakage, release별 license 확정, model metric은 남은 항목이며 이 준비 결과로 검증 완료를 주장하지 않는다.
