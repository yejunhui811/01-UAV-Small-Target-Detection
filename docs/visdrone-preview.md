# VisDrone annotation preview

이미지 한 장의 원본 annotation을 검토하는 도구이다. **모델 prediction이나 failure analysis 결과가 아니다.** 합성 테스트와 실제 train/val 각각 한 장의 GT preview를 확인했다. [준비 기록](datasets/visdrone2019-det-2026-10-08/README.md)을 따른다. 실제 이미지는 로컬에만 보관한다. 기존 `Pillow==12.3.0`을 사용하며 새 dependency는 추가하지 않는다.

## Synthetic demo

[Setup](../README.md#setup)에 따라 가상환경을 준비한 뒤 저장소 root에서:

```bash
source .venv/bin/activate
python scripts/preview_visdrone.py --demo \
  --output-dir outputs/visdrone-preview/synthetic-demo-v1
```

임시 폴더에서 작은 PNG/TXT를 생성·제거하고 지정한 새 폴더에 `preview.png`, `manifest.json`을 저장한다. 이미지 제목과 JSON `source_kind`에 합성 데모임을 표시한다. 랜덤 생성이나 데이터 다운로드는 하지 않는다. 다시 실행하려면 다른 새 output directory 이름을 사용한다.

`outputs/`는 Git에서 제외되며 이 그림은 README의 연구 결과에 추가하지 않는다.

## Future local data usage

**아래는 임의의 로컬 pair를 검토하는 사용 예시이다. 실행한 두 sample의 기록은 snapshot 안내를 따른다.** 전체 dataset 상태는 먼저 [validator](visdrone-validation.md)로 확인한다.

```bash
python scripts/preview_visdrone.py \
  --root data/visdrone/visdrone2019-det/raw \
  --split val \
  --image-stem IMAGE_STEM \
  --output-dir outputs/visdrone-preview/val-IMAGE_STEM-001
```

`IMAGE_STEM`은 `.jpg`/`.png`/`.txt` 확장자를 뺀 실제 파일명으로 바꾼다. `train`, `val`, labeled `test-dev`를 지원한다. stem은 대소문자를 구분하며 이미지(JPG/JPEG/PNG)와 TXT가 각각 한 개씩 있어야 한다. 누락·이름 충돌·경로 형태의 stem은 거부한다. 이 도구는 GT용이며 detection confidence 파일을 지원하지 않는다.

## Display policy

- 원본 픽셀 xywh로 bbox를 읽고 이미지를 resize하거나 EXIF orientation으로 회전하지 않는다. [원본 class ID/name](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/005445782213e20cb91bc50a597db3dd949e749a/README.md)을 유지하며 모델 class ID로 변환하지 않는다.
- 녹색: score 1, category 1..10 target. 노란색: score 0 또는 category 0 ignored. 보라색: score 1/category 11 other.
- 빨간색: `x < 0`, `y < 0`, `x + width > W`, `y + height > H`인 bbox. 색상은 원본 class를 바꾸지 않으며 JSON에는 kind와 경계 여부를 별도로 보존한다.
- 화면에서는 bbox와 이미지의 교집합만 그린다. 연속 범위의 왼쪽·위쪽은 floor, 오른쪽·아래쪽은 ceil에서 1을 뺀 inclusive pixel endpoint를 사용한다. [Pillow rectangle 정의](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html#PIL.ImageDraw.ImageDraw.rectangle)를 따르는 프로젝트의 표시 규칙이며 공식 evaluator 좌표 동등성은 미검증이다. 원본 label을 clipping하거나 저장하지 않는다.
- 완전히 화면 밖인 bbox와 float 연산에서 크기 범위가 사라진 bbox는 그리지 못한다. 원본 좌표·line number와 경고를 JSON에 남긴다.
- 그릴 공간이 있으면 bbox 옆에 `L행번호 category:name`을 표시한다. 작은 이미지에서는 inline label을 생략할 수 있다. 오른쪽 목록에는 첫 20개 유효 row의 class·kind·원본 xywh·score를 표시하며 JSON에는 모든 유효 row가 남는다. 밀집·겹침·작은 객체에서는 label이 겹칠 수 있으므로 JSON과 원본을 함께 검토한다.
- 숫자·필드·score/category·bbox-size 오류 행은 건너뛰되 line number와 모든 core 오류를 기록하고 `PARTIAL` 배너를 표시한다. [공통 parser](../src/uav_small_target/visdrone_annotations.py)를 validator와 공유한다. 빈 annotation과 unusual attributes는 검토 경고이다.

## Outputs and exit codes

`preview.png`는 header·원본 크기 이미지·옆 목록·범례로 구성된다. JSON `image_offset_in_preview`가 전체 preview 안의 원본 이미지 시작 위치이다.

`manifest.json`은 scope, source kind, 상대 input 경로, input SHA-256, Pillow 버전, 원본 이미지 크기, 표시 좌표 정책, valid/invalid/drawn row 수량, 오류·경고 및 row별 원본 8개 값을 기록한다. 수량은 시각화 처리 내역이며 모델 metric이 아니다. 실제 데이터 검토 때는 실행 command·Git commit도 [데이터 준비 기록](dataset-record-template.md)에 함께 남긴다.

| CLI exit code | 의미 |
| --- | --- |
| 0 | preview 저장 완료; warning 여부는 JSON 확인 |
| 1 | invalid annotation row가 있어 partial preview 저장; 수정 또는 원본 검토 필요 |
| 2 | 인자·pair·dependency·UTF-8·이미지 decoding·저장 오류 등으로 작업 미완료 |

stdout은 JSON, stderr는 짧은 결과/오류 안내이다. output directory는 raw root 밖이어야 하며 symlink도 실제 경로로 확인한다. **기존 directory는 비어 있어도 거부**한다. 원본·이전 output은 덮어쓰지 않는다. 저장 도중 I/O 오류가 발생하면 새 directory에 일부 파일이 남을 수 있으므로 완료 여부를 exit code로 확인하고 새 경로에서 재실행한다.

이미지는 strict single-frame JPEG/PNG verify·load를 거치며 Pillow 픽셀 제한을 유지한다. 손상 이미지와 잘못된 UTF-8은 partial preview 없이 중단한다. 결과가 `ready`여도 한 pair를 그릴 수 있었다는 뜻일 뿐 전체 dataset 준비 완료를 의미하지 않는다. 이미지 내용 오류, scene leakage, release 조건, 공식 evaluator와 모델 성능은 검사하지 않는다.

## Validation

```bash
python -B -m unittest discover -s tests -v
python -B scripts/validate_structure.py
```

[Preview tests](../tests/test_visdrone_preview.py)는 합성 PNG/JPEG/TXT로 pixel 좌표·색상, class/ignore 보존, 경계·소수·offscreen, parser 일치, partial/empty output, decoding/UTF-8, EXIF, overwrite·raw 보호, CLI와 반복 출력 일치를 확인한다. 합성 테스트에서 실제 데이터를 사용하지 않는다. 실제 pair preview 실행과 모델 실험은 구분한다.
