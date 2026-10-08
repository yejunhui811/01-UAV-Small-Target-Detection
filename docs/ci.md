# GitHub Actions CI

[CI workflow](../.github/workflows/ci.yml)는 GitHub-hosted **Ubuntu 24.04 / Python 3.11**에서 repository 검증을 자동 실행한다. branch push, `main` 대상 Pull Request, 수동 실행(`workflow_dispatch`)을 지원한다. tag push는 대상이 아니다. 수동 실행은 workflow가 default branch에 반영된 뒤 GitHub Actions 탭에서 사용할 수 있다.

## What runs

1. 코드 checkout 및 Python 3.11 준비
2. Python/pip 버전과 실제 검사한 checkout commit 출력
3. `requirements.txt` 및 CPU-only `requirements-metrics.txt` 설치 후 `pip check` (PyTorch/YOLO 미설치)
4. 전체 합성 `unittest` 실행
5. `python -S`로 site packages를 제외한 기존 metadata 테스트 실행
6. 구조·로컬 문서 링크 경로·TOML·ignore·tracked 파일 검증
7. `git diff --check HEAD^ HEAD` 실행: PR에서는 GitHub의 test merge commit과 첫 번째 parent인 base 사이의 변경을, push에서는 마지막 commit의 변경을 검사한다. 전체 코드 검토를 대신하지 않는다. 이를 위해 checkout 시 2단계 이력을 가져온다.

테스트 fixture는 임시 합성 PNG/JPEG/TXT이며 종료 시 제거한다. 실제 VisDrone 다운로드, model weights 준비, 학습·추론·benchmark는 실행하지 않는다. 패키지 설치와 Actions 준비에는 네트워크를 사용한다. 테스트의 통과는 연구 성능 결과가 아니다.

`permissions: contents: read`로 읽기 권한만 요청하고 checkout 인증정보는 이후 단계에 저장하지 않는다. Actions는 검토한 commit SHA로 고정하며 버전 주석을 함께 기록한다. 같은 branch/PR에 새 commit이 들어오면 해당 ref의 이전 실행을 취소한다. job 제한 시간은 10분이다.

Python `3.11`은 patch 버전 범위이며 Ubuntu runner 이미지도 갱신될 수 있다. 실제 환경은 run의 버전 출력과 setup/install 로그로 확인한다. 이 CI는 모델·CUDA 환경 lock을 제공하지 않는다. 로컬 문서 URL의 원격 접속과 Markdown anchor, 이미지 내용의 시각적 품질, 공식 evaluator 및 GPU 경로는 검사하지 않는다.

## How to review a run

- PR 페이지의 Checks에서 `CI` / `Validation (Python 3.11)`을 확인한다.
- Actions 탭에서 해당 branch와 commit의 run을 열고 각 step의 결과·로그를 확인한다. push와 PR로 별도 run이 생길 수 있다.
- 초록색 성공은 그 run에서 설정한 검사가 통과했다는 뜻이다. 실패하면 실패 step의 로그를 읽고 수정 commit을 push한다.
- 실행 취소·대기·skipped·실행 없음은 통과가 아니다. 새 commit을 추가하면 그 commit의 검사 결과를 다시 확인한다.
- CI가 통과해도 Files changed에서 코드·문서·데이터 포함 여부를 검토하고, 사용자 승인 후 merge한다.

이 workflow는 자동 merge나 branch protection 설정을 변경하지 않는다. merge 차단이 필요하면 추후 GitHub 설정에서 이 check를 required status check로 별도 지정한다.

## Run the same checks locally

저장소 root에서 [Setup](../README.md#setup)에 따라 가상환경을 준비한 후:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-metrics.txt
python -m pip check
python -B -m unittest discover -s tests -v
python -S -B -m unittest discover -s tests -p test_visdrone_validation.py -v
python -B scripts/validate_structure.py
git diff --check
```

로컬 macOS 결과와 GitHub Ubuntu 결과는 구분한다. 전체 테스트 범위는 [tests 안내](../tests/README.md), dependency는 [환경 정책](dependencies.md)을 따른다. workflow 작성 방식은 [GitHub 공식 Python CI 문서](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), action 정의는 [checkout](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1)과 [setup-python](https://github.com/actions/setup-python/tree/5fda3b95a4ea91299a34e894583c3862153e4b97)을 참고한다.
