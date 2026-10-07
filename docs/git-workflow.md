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
branch는 작업을 분리한다. 위 이름은 이후 baseline 구현을 위한 예시이고 이번 bootstrap에서는 `setup/project-bootstrap`을 사용한다.

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

이번 bootstrap 작업은 branch push까지 진행하고 PR 생성 전에 멈춘다. 사용자는 GitHub branch 선택 메뉴에서 `setup/project-bootstrap`의 파일을 보고, main과 비교한 뒤 PR 생성 여부를 결정할 수 있다.
