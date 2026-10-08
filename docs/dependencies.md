# Dependency strategy

초기 개발 기준은 Python 3.11이다. bootstrap 환경에 설치되어 있고 TOML을 표준 라이브러리 `tomllib`로 읽을 수 있어, 현재 구조 검증에 별도 패키지가 필요하지 않다. 이는 향후 모든 모델·GPU 환경과의 호환성을 보장하는 선택이 아니다.

`requirements.txt`는 **Pillow==12.3.0**만 포함한다. JPEG/PNG decoding과 크기 검사가 필요한 `--check-images` 기능에 사용하며, Python 3.11.9 / macOS arm64 가상환경에서 설치·import·합성 테스트와 `pip check`를 검증했다. 고정 버전은 [PyPI 배포 정보](https://pypi.org/project/pillow/12.3.0/)에서 확인하고 실제 설치한 버전이다. [CI](ci.md)는 Ubuntu 24.04 / Python 3.11을 대상으로 구성하며 실제 실행 결과와 버전은 각 commit의 Actions 로그로 확인한다. 그 외 OS/Python 조합은 아직 검증하지 않았다.

Pillow는 `Image.open()` 후 `verify()`, 재열기 후 `load()`로 컨테이너와 실제 픽셀 decoding을 검사한다. [공식 Image API](https://pillow.readthedocs.io/en/stable/reference/Image.html)를 따른다. 기본 metadata 검사와 구조 검증은 표준 라이브러리만 사용하며 Pillow는 이미지 검사 요청 시에만 import한다. 이미지 검사 요청 시 미설치 상태면 CLI exit code 2와 설치 안내를 반환한다.

전체 합성 테스트를 실행하는 로컬 환경:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -B -m unittest discover -s tests -v
```

PyTorch, Ultralytics, RT-DETR 관련 패키지는 baseline 구현 시 실제 사용할 구현체와 CPU/GPU 환경을 정하고 호환성을 검증한 뒤 추가한다. 불필요한 패키지를 미리 설치하지 않는다.

향후 dependency 도입 시:
1. 기능에 필요한 직접 dependency와 검증한 버전을 `requirements.txt`에 기록한다.
2. 모델 framework, Python, CUDA/driver의 조합을 실제 환경에서 확인한다. 장치별 설치 방식이 다르면 별도 파일과 명령으로 문서화한다.
3. 각 실행 환경의 transitive dependency snapshot을 기록한다. 경로·private index·token이 포함되지 않았는지 검토한다.
4. `pip check`, import 및 필요한 sample 실행을 검증하고 환경 정보를 실험 기록에 연결한다.

현재 파일은 완전한 환경 lock이 아니다. 모델 실행 전에는 검증된 버전 pin과 환경 snapshot을 갖춘다. `.venv/`는 로컬 전용이며 commit하지 않는다.
