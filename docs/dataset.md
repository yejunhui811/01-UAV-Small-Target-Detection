# Dataset management

계획한 dataset은 VisDrone이다. 정확한 release, split 및 이용 조건은 baseline 구현 전에 확인한다. 이번 단계에서는 dataset을 다운로드하거나 변환하지 않는다.

권장 로컬 경로는 `data/visdrone/<release>/`이다. `data/`와 `datasets/` 전체는 Git에서 제외한다. 해당 폴더는 사용자가 데이터를 준비할 때 생성하며 repository의 tracked 구조에는 포함되지 않는다. dataset 위치는 [설정 양식](../configs/experiment.example.toml)의 `dataset.root`에 기록한다.

실제 데이터 도입 시 기록할 항목:
- 공식 출처, release/version, 다운로드 날짜, 이용·재배포 조건
- 원본 archive 또는 file manifest의 SHA-256 (manifest는 검토 후 작은 문서로 관리)
- train/validation/test split, 이미지 수, 중복·누수 확인 결과
- annotation 형식, class mapping, ignored regions/labels 처리 규칙
- 변환 스크립트와 commit, 검증 절차, 변환 후 dataset version

원본 데이터를 보존하고 파생 데이터는 구분한다. GitHub에는 raw media/annotations/archive 대신 관리 문서, 설정과 변환 코드를 둔다. 통계도 실제 데이터를 확인한 뒤에만 기록한다. 데이터 경로나 artifact URL에 credentials를 넣지 않는다.
