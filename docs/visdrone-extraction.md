# Local VisDrone archive extraction

실제 데이터 다운로드는 사용자가 허용한 준비 단계에서만 수행한다. 공식 [VisDrone 배포 README](https://github.com/VisDrone/VisDrone-Dataset)에서 연결한 Google Drive train/val archive를 사용한다. train/val만 준비하며 test-dev·test-challenge는 이번 범위에 포함하지 않는다. 이용 조건·출처·다운로드 시간·크기와 SHA-256을 [데이터 기록](dataset-record-template.md)에 남긴다. 원본 ZIP과 데이터는 로컬 `data/`에만 보관한다.

## Download

저장소 root에서 새 작업 영역을 만들고 기존 파일이 없는지 먼저 확인한다. 다음은 공식 링크의 파일 ID를 사용하는 command이다. 내려받는 도중에는 `.part` 이름을 쓰며 오류 시 최종 ZIP으로 취급하지 않는다. ZIP 크기·구조를 확인한 뒤 `.zip`으로 바꾼다. 기존 파일을 덮어쓰거나 부분 다운로드를 무조건 정상 데이터로 취급하지 않는다.

```bash
mkdir -p data/visdrone/visdrone2019-det/archives
curl --location --fail --retry 3 \
  --output data/visdrone/visdrone2019-det/archives/VisDrone2019-DET-train.zip.part \
  'https://drive.usercontent.google.com/download?id=1a2oHjcEcwXP8oUF95qiwrqzACb2YlUhn&export=download&confirm=t'
curl --location --fail --retry 3 \
  --output data/visdrone/visdrone2019-det/archives/VisDrone2019-DET-val.zip.part \
  'https://drive.usercontent.google.com/download?id=1bxK5zgLn0_L8x276eKkuYA_FzwCIjb59&export=download&confirm=t'
```

HTTP 200 자체로 진위·무결성을 보장하지 않는다. 프로젝트의 실제 archive fingerprint와 확인 결과는 해당 snapshot 기록을 따른다. 공식 인증 hash와 로컬 계산 hash를 구분한다. HTML 오류 페이지가 저장된 경우 ZIP으로 받아들이지 않는다.

## Extract and record

다운로드와 ZIP 이름 확정 후, raw와 extraction metadata는 아직 없는 directory를 지정한다:

```bash
python -B scripts/extract_visdrone.py \
  --archive-dir data/visdrone/visdrone2019-det/archives \
  --raw-root data/visdrone/visdrone2019-det/raw \
  --metadata-dir data/visdrone/visdrone2019-det/metadata/extraction-v1
```

Python 표준 라이브러리만 사용한다. ZIP의 경로 이탈·절대 경로·backslash·special file/symlink·중복/case collision을 거부한다. 각 archive의 첫 directory는 archive basename과 일치해야 한다. archive당 최대 30,000 entries / 20 GiB uncompressed 제한을 적용한다. 이는 현재 DET train/val용 제한이며 모든 데이터셋을 지원하는 일반 extractor가 아니다.

모든 파일은 streaming extraction을 통해 ZIP CRC와 uncompressed size를 확인한다. 원본 archive와 추출 파일의 SHA-256, 상대 경로, 파일 크기를 `extraction.json` 및 `file-manifest.jsonl`에 기록한다. 압축 해제는 원본 내용을 수정하지 않으며 `.DS_Store` 같은 ancillary 파일도 보존·기록한다. label 의미와 이미지 decoding은 검사하지 않으므로 다음 validator 단계가 필요하다.

입력 오류 시 임시 staging을 정리하고 output을 공개하지 않는다. 기존 raw/metadata directory는 비어 있어도 거부한다. 최종 publication은 두 directory에 여러 파일을 이동하므로 atomic하지 않다. 저장 오류나 강제 종료 시 새 불완전 output 또는 `.uav-extract-*` staging이 남을 수 있다. CLI exit 0은 extraction/기록 완료, exit 2는 실패이다. 기존 사용자 파일을 자동 삭제하지 않는다.

## Validate and convert

```bash
python -B scripts/validate_visdrone.py \
  --root data/visdrone/visdrone2019-det/raw --splits train val \
  --check-images --check-duplicates \
  --report data/visdrone/visdrone2019-det/metadata/validation-v1.json
python -B scripts/convert_visdrone_yolo.py \
  --root data/visdrone/visdrone2019-det/raw --splits train val \
  --zero-area-policy exclude \
  --output-dir data/visdrone/visdrone2019-det/derived/visdrone-yolo-v2
```

위 경로의 report/output이 있으면 새로운 version 이름을 사용한다. [Validator](visdrone-validation.md)와 [변환 정책](visdrone-yolo.md)의 오류·경고·제외 규칙을 따르며 변환 전후 count/hash/sample을 비교한다. 실제 결과는 [snapshot 기록](datasets/visdrone2019-det-2026-10-08/README.md)에 기록한다. 모델 성능 수치와 데이터 처리 수량을 구분한다.
