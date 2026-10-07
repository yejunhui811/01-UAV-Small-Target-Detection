# Dataset acquisition record: <snapshot-id>

Status: planned — not downloaded or validated. 이 파일은 미기입 양식이다. 실제 준비 작업 후 확인한 항목만 채우고, 미확인 항목을 0 또는 완료로 표시하지 않는다.

## Identity and provenance

- Dataset / task / release:
- Snapshot ID and local relative root:
- Official source URL / document commit / checked date:
- Archive acquisition date with timezone:
- Applied terms / release-specific evidence / checked date:
- Terms status: pending / verified / unresolved (select after checking)
- Permitted use and image/figure sharing restrictions:
- Citation to include:

## Archives

| Split | Exact filename | Source URL (without credentials) | Size (bytes) | Computed SHA-256 | Official hash comparison, if available |
| --- | --- | --- | --- | --- | --- |
| train | | | | | |
| val | | | | | |
| test-dev (optional) | | | | | |

## Local validation

- Validation status / date / command / code commit:
- Actual image and annotation counts per split / published expectation comparison:
- Missing, corrupt or unmatched files:
- Annotation field/category/score/coordinate checks:
- Bbox exceptions and handling rationale:
- Cross-split exact duplicate check / near-duplicate check / limitations:
- File manifest relative path and SHA-256:
- Validation report relative path and SHA-256:

## Conversion and reproducibility

- Original annotation format / class mapping / ignored label policy:
- Conversion version / exact code commit / command / environment:
- Derived output relative root / manifest hash:
- Original and converted sample comparison:
- Count changes / removed or modified items and reasons:
- Any seed / deterministic settings required:
- Evaluator version / ignored region handling / coordinate convention:

## Readiness and limitations

- Acquisition, terms and validation items completed:
- Outstanding items:
- Ready for the next implementation step: undecided (set only with evidence)
- Link to the associated experiment record when execution begins:

로컬 기록은 `data/visdrone/<release>/metadata/`에 둔다. 공유할 때는 [관리 정책](dataset.md)에 따라 raw annotation, private 경로·URL, credentials가 없는 요약만 검토 후 commit한다.
