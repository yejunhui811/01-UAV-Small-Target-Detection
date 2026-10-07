# Git workflow for this project

## Start from a known state
```bash
git status
git branch --show-current
git log --oneline -n 5
git remote -v
```
현재 파일 변경, branch, commit과 GitHub 연결을 확인한다. 기존 변경사항이 있으면 먼저 보존한다.

## Create a work branch
깨끗한 main에서 새 작업을 시작할 때의 예시:
```bash
git switch main
git pull --ff-only origin main
git switch -c feature/yolo-baseline
```
branch는 작업을 분리한다. 위 이름은 이후 baseline 구현을 위한 예시이다. 초기 구조는 `setup/project-bootstrap`에서 작업한 뒤 사용자 승인에 따라 [PR #1](https://github.com/yejunhui811/01-UAV-Small-Target-Detection/pull/1)로 main에 merge했다. 새 작업은 최신 main에서 목적에 맞는 별도 branch로 시작한다.

## Validate, stage, commit
```bash
python3 scripts/validate_structure.py
git diff --check
git status
git diff
git add README.md
git diff --cached
git commit -m "Document validated baseline setup"
```
예시의 `git add README.md`는 README만 다음 commit 대상으로 선택한다. 실제 작업에 맞춰 검토한 파일을 선택한다. commit은 local history의 체크포인트이며 아직 GitHub에는 없다.

## Push and review
```bash
git push -u origin feature/yolo-baseline
```
push는 local commit을 GitHub remote의 작업 branch에 업로드한다. `-u`는 이후 push/pull에 사용할 추적 branch를 연결한다. push만으로 main에 반영되지는 않는다.

Pull Request는 GitHub에서 base `main`과 compare 작업 branch의 차이를 검토하는 단계이다. 변경 파일, 검증 결과, conflict, 데이터·비밀정보 포함 여부, 실제 연구 근거를 확인하고 사용자가 merge를 허가해야 main에 반영한다.

PR에서 base `main`, compare 작업 branch가 맞는지 확인하고, Files changed에서 변경사항을 검토한다. PR 생성과 push만으로는 main에 반영되지 않는다. 사용자의 명시적 승인 후 merge하면 작업 내용이 main에 반영된다.

## Sync main after merge

GitHub에서 merge를 완료한 뒤, 로컬 변경사항이 없는지 `git status`로 확인하고 main을 동기화한다:

```bash
git switch main
git pull --ff-only origin main
```

`git switch main`은 로컬 main으로 전환한다. `git pull --ff-only origin main`은 GitHub의 main을 가져와 로컬 main을 업데이트하며, 이력이 갈라져 있으면 자동 merge 대신 중단한다. 다음 작업은 동기화한 main에서 새 branch를 만들어 시작한다.
