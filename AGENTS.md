# Project operating rules

## Project principle
- 이 저장소는 UAV small target detection 연구 및 취업 포트폴리오 프로젝트이다.
- 연구 결과의 재현성과 정확성을 최우선으로 한다.
- 실제 실행하지 않은 실험 결과나 metric을 임의로 작성하지 않는다.
- 확인할 수 없는 수치를 추정해서 README에 넣지 않는다. 계획, 가설, 측정된 결과를 명확히 구분한다.

## Git workflow
- `main`은 안정적인 branch로 취급한다.
- 의미 있는 기능, 실험, refactor, bug fix는 별도 branch에서 수행한다.
- branch 생성 전에 `git status`, `git branch --show-current`, `git log --oneline -n 5`와 remote를 확인한다.
- 기존 사용자의 작업을 임의로 삭제하거나 덮어쓰지 않는다.
- 구현 후 검증을 먼저 수행한다. commit 전 `git status`, `git diff`, `git diff --cached`를 검토한다.
- 의미 있는 작업 단위로 commit한다. 데이터, 비밀정보, 대용량 파일이 staging에 포함되지 않았는지 확인한다.
- 작업 branch를 push한 뒤 사용자의 명시적 허가 없이 `main`에 merge하지 않는다.
- 사용자가 정한 종료 지점을 지킨다. PR 생성 권한과 merge 권한을 구분한다.

Branch 이름 예:
- `feature/yolo-baseline`
- `feature/rtdetr-baseline`
- `feature/tiled-inference`
- `feature/evaluation-metrics`
- `experiment/input-resolution-1280`
- `experiment/mosaic-augmentation`
- `fix/dataset-loader`
- `docs/update-readme`

## Beginner Git learning mode
사용자는 Git/GitHub 초보자이다. 중요한 Git 작업이 실제로 발생할 때, 현재 작업에 연결해 한두 문장으로 설명한다. 장황한 강의는 하지 않는다.
- branch: 작업 내용을 분리하는 공간이며, merge 전에는 다른 branch에 반영되지 않는다.
- `git add`: 다음 commit에 포함할 변경사항을 staging area에 선택한다.
- commit: 변경사항을 local Git history에 체크포인트로 저장한다. 아직 GitHub에 업로드된 것은 아니다.
- local repository: 사용자 컴퓨터의 파일과 Git 이력이다. GitHub remote: 온라인 저장소의 파일과 Git 이력이다.
- push: local commit을 GitHub remote의 해당 branch에 업로드한다. push 자체는 main으로 merge하지 않는다.
- Pull Request: 작업 branch와 main의 차이를 검토하고 merge 여부를 결정하는 단계이다.
- merge 전: 변경 범위, 검증 결과, conflict, 데이터·비밀정보 포함 여부, 연구 수치의 실제 근거를 확인한다.

## Validation policy
변경 범위에 맞게 syntax error, import error, runtime error, dependency 문제, 기존 기능 regression, configuration loading, CPU/GPU device 처리, sample inference, evaluation script를 검증한다.
- 기반 구조만 변경했다면 구조, 문서 경로·링크, ignore 규칙, 설정 parsing과 검증 스크립트 실행을 확인한다.
- 학습·추론 코드가 추가되면 관련 항목을 추가 검증한다. GPU가 없으면 CPU 경로와 GPU 미검증 사실을 구분한다.
- 전체 검증이 불가능하면 실행한 검증과 실행하지 못한 검증 및 이유를 보고한다.
- 사용자가 이번 단계에 학습, 데이터 다운로드, benchmark를 금지했다면 검증 명목으로 실행하지 않는다.

## Research integrity
- 실험하지 않은 결과 작성 및 fabricated metric을 금지한다.
- 실제 output과 README의 결과를 일치시킨다. 실패한 실험과 불확실성도 기록한다.
- experiment configuration, 실행 명령, Git commit, dataset release/split/version/checksum, model variant/weights version, seed, Python/package/hardware/device 정보를 가능한 한 기록한다.
- 비교 실험에서는 데이터 분할, 평가 규칙, 측정 조건을 맞추고 변경한 변수를 명시한다.
- `AP_small`의 면적 기준과 좌표계, FPS/latency의 batch size·warm-up·측정 범위·장치 동기화 기준을 명시한다.
- 재현 구조는 [실험 기록 안내](experiments/README.md), [실험 양식](experiments/template.md), [설정 양식](configs/experiment.example.toml)을 따른다.
- 측정 전 metric은 비워 두거나 `not measured`로 표시한다. 0을 미측정 값으로 사용하지 않는다.

## Files that must not be committed
특별한 이유와 사용자의 명시적 동의가 없는 한 다음을 commit하지 않는다:
- datasets 및 raw images/videos
- model weights: `.pt`, `.pth`, `.ckpt` 및 대형 model/export artifacts
- `.env`, API keys, secrets, 인증정보 및 비공개 환경 snapshot
- cache, Python `__pycache__`, 대용량 training outputs, 불필요한 temporary files

`.gitignore`를 유지한다. 로컬 dataset은 `data/`, model weights는 `weights/`, 실행 output은 `outputs/`에 둔다. 결과 문서와 작은 검토된 figure/table만 `results/`에 추가한다. `.gitignore`는 이미 tracked된 파일이나 임의 파일 안의 비밀정보를 제거하지 않으므로 diff도 검토한다.

## End-of-task report
의미 있는 작업이 끝나면 다음 형식으로 간략히 보고한다:

### Work completed
- 구현/수정한 내용

### Validation
- 통과한 검증
- 테스트하지 못한 항목과 이유

### Git status
- 현재 branch
- commit message / commit hash
- push 여부

### What this means in Git
working directory에만 있는지, local commit까지 된 것인지, GitHub remote branch까지 올라간 것인지, main에 merge된 것인지를 초보자도 이해할 수 있는 한두 문장으로 설명한다.

### Recommended next step
다음 Git/GitHub 작업과 확인할 내용을 안내한다.
