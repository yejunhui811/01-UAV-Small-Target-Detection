# VisDrone metadata validator

현재 구현은 **파일 대응과 annotation metadata 검사**이다. Python 3.11 표준 라이브러리만 사용하고 원본을 읽기만 한다. 데이터 다운로드, label 변환·삭제·clipping, 학습·추론·모델 metric 계산은 수행하지 않는다. [데이터 준비 계획](dataset.md)의 전체 checklist 중 일부를 구현한 것이며, 실제 VisDrone 데이터에서는 아직 실행하지 않았다.

## Input and command

`--root`는 `VisDrone2019-DET-train/`, `VisDrone2019-DET-val/`, 선택적으로 `VisDrone2019-DET-test-dev/`가 들어 있는 raw 디렉터리이다. 각 split에는 직접적인 `images/`와 `annotations/` 디렉터리가 있어야 한다. 중첩된 폴더는 재귀 검색하지 않는다. 이미지 확장자는 JPG/JPEG/PNG, annotation은 TXT이며 stem(확장자를 뺀 파일명)을 대소문자 구분해 비교한다.

먼저 도움말만 확인할 수 있다:

```bash
python3 scripts/validate_visdrone.py --help
```

**아래 명령은 실제 데이터가 준비된 후 사용할 예시이며 이번 단계에서 실행하지 않았다.** 로컬 경로는 [보관 구조](dataset.md)에 맞춘다.

```bash
python3 scripts/validate_visdrone.py \
  --root data/visdrone/visdrone2019-det/raw \
  --splits train val \
  --check-duplicates \
  --report outputs/visdrone-validation/initial.json
```

기본 split은 `train val`이다. `test-dev`는 label이 준비된 경우에만 선택한다. label이 없는 `test-challenge`는 지원하지 않는다. `--check-duplicates`는 선택 사항이며 이미지 전체 bytes를 SHA-256으로 읽어 추가 I/O가 발생한다.

JSON은 stdout으로, 짧은 상태 요약은 stderr로 출력한다. `--report`를 주면 동일 JSON도 저장한다. report는 dataset root 밖에 있어야 하며 기존 파일을 덮어쓰지 않는다. 재실행 시 새 파일명을 사용한다. report에는 로컬 검사 수량·문제 경로만 들어가며 연구 성능 결과가 아니다. `outputs/`는 Git에서 제외된다.

## Checks and interpretation

| 검사 | 처리 |
| --- | --- |
| 필수 directory·image/TXT 없음, file stem 누락·충돌 | error |
| zero-byte image, 읽기 실패·annotation UTF-8 오류 | error |
| annotation 8개 필드, numeric/finite 값 | 위반 시 error; optional terminal comma 하나 허용 |
| GT score 0/1, category 0..11, 정수 metadata | 위반 시 error |
| bbox 폭·높이 양수 | 위반 시 error |
| 음수 bbox 원점 | warning; 원본 좌표·truncation 정책 검토, clipping 없음 |
| truncation 0/1 또는 occlusion 0/1/2 밖의 값 | warning; release 원본 규칙 확인, 삭제 없음 |
| empty annotation | warning; 정상 negative image 가능성도 있어 review 필요 |
| split 간 동일 image bytes | `--check-duplicates` 사용 시 error |
| split 내부 동일 image bytes | `--check-duplicates` 사용 시 warning |

score 0 또는 category 0/11인 row는 `ignored_or_other_rows`로 따로 집계한다. 그 외 유효한 core row는 `target_rows`로 집계한다. `valid_core_rows`와 원본 class count는 필수 numeric/score/category/bbox-size 검사를 통과한 row만 센다. warning이 있는 row도 집계될 수 있다. ignore row를 삭제하거나 모델용 class로 변환하지 않는다.

`status`는 error가 있으면 `failed`, warning만 있으면 `warning`, 둘 다 없으면 `passed`이다. **passed는 이 검사 범위에서 문제를 찾지 않았다는 뜻이며, 전체 데이터 검증이나 학습 준비 완료를 뜻하지 않는다.** 실제 출력은 [준비 기록 양식](dataset-record-template.md)에 검사 command/code commit과 함께 기록한다.

| CLI exit code | 의미 |
| --- | --- |
| 0 | 검사 완료, error 없음; warning 여부는 JSON을 확인 |
| 1 | 검사 완료, 데이터 error 발견 |
| 2 | CLI 인자·root·보고서 저장 문제 등으로 작업 미완료 |

## Limits

JSON `not_checked`에는 이미지 전체 decoding, 이미지 크기에 대한 bbox 경계, near-duplicate/scene leakage, archive 무결성, release·이용 조건, 공식 evaluator 동등성, 모델 metric을 명시한다. 비어 있지 않은 손상 이미지도 이 버전만으로는 통과할 수 있다. 추후 실제 데이터와 decoder 도입 시 별도 검증이 필요하다.

SHA-256 일치는 **파일 bytes의 완전 중복**만 찾는다. 이미지 내용이 같아도 압축이나 metadata가 다르면 검출하지 못한다. 중복 검사를 생략하면 `duplicate_check`가 `not_run`으로 표시된다. 제공된 실제 split 수량과의 비교도 별도 기록이 필요하다.

## Synthetic verification

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/validate_structure.py
```

합성 PNG/TXT를 임시 폴더에 만들어 정상·오류·CLI 동작을 검사한다. 실제 VisDrone 검증·변환이나 모델 실험은 하지 않았다. 테스트 코드는 [tests/test_visdrone_validation.py](../tests/test_visdrone_validation.py), 재사용 API는 [src/uav_small_target/visdrone_validation.py](../src/uav_small_target/visdrone_validation.py)에 있다.
