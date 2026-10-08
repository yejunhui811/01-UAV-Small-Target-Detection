# Tests

저장소 root에서 Pillow를 설치한 가상환경으로 전체 테스트를 실행:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
```

`test_visdrone_validation.py`는 Python 표준 라이브러리로 작은 PNG와 TXT를 임시 폴더에 생성하고 종료 시 제거한다. 정상 metadata, 잘못된 필드·숫자·enum·bbox, missing pairs, 이름 충돌, 빈 파일, UTF-8 오류, exact duplicates, CLI 종료 코드·JSON, 원본 보존과 report 덮어쓰기 방지를 검증한다. fixture는 synthetic이며 실제 VisDrone 샘플이나 연구 결과가 아니다.

`test_visdrone_images.py`는 Pillow로 임시 PNG/JPEG를 생성한다. 픽셀 decoding, PNG checksum·압축 스트림 오류, 잘린 JPEG, 경계 밖 bbox·정확한 경계·소수 좌표, EXIF 원본 좌표계, multi-frame 거부, 픽셀 제한, 누락·충돌·decoding 실패에 따른 bbox 검사 생략, 원본 보존, CLI 옵션·dependency 오류를 검증한다.

Pillow 없이 기존 metadata 테스트만 확인할 때는 `python3 -B -m unittest discover -s tests -p test_visdrone_validation.py -v`를 사용한다. 전체 테스트는 Pillow가 필요하다. GPU/모델 실행, 실제 VisDrone dataset와 공식 evaluator는 테스트하지 않는다. 각 검증 범위는 [validator 안내](../docs/visdrone-validation.md)를 따른다.

[GitHub Actions CI](../docs/ci.md)는 Ubuntu 24.04 / Python 3.11에서 전체 합성 테스트, site packages 없는 metadata 테스트와 구조 검증을 실행한다. 실제 성공 여부는 해당 commit의 PR Checks 또는 Actions 로그를 확인한다.
