# Tests

저장소 root에서 실행:

```bash
python3 -B -m unittest discover -s tests -v
```

`test_visdrone_validation.py`는 Python 표준 라이브러리로 작은 PNG와 TXT를 임시 폴더에 생성하고 종료 시 제거한다. 정상 metadata, 잘못된 필드·숫자·enum·bbox, missing pairs, 이름 충돌, 빈 파일, UTF-8 오류, exact duplicates, CLI 종료 코드·JSON, 원본 보존과 report 덮어쓰기 방지를 검증한다. fixture는 synthetic이며 실제 VisDrone 샘플이나 연구 결과가 아니다.

실제 이미지 decoding, GPU/모델 실행, 실제 dataset와 공식 evaluator는 테스트하지 않는다. 각 검증 범위는 [validator 안내](../docs/visdrone-validation.md)를 따른다.
