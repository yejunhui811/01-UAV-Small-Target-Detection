# Results

이 디렉터리에는 실제 실행 후 검토한 작은 연구 산출물만 둔다. 첫 [YOLO11n 1-epoch pilot](../experiments/exp-002-yolo11n-pilot-mps/README.md)의 측정 CSV와 원본 면적별 AP plot을 기록했다. 본학습 완료·공식 VisDrone 점수로 해석하지 않는다.

- [figures/](figures/): 설명 가능한 비교 그림, plot, 공유 가능한 시각화
- [tables/](tables/): 실제 측정 결과를 정리한 표

각 산출물은 experiment ID, 설정, code commit과 원본 output 위치를 추적할 수 있어야 한다. raw predictions/logs, weights, 대형 영상은 `outputs/` 또는 외부 artifact 보관소에 둔다. figure/GIF는 데이터셋의 공유 조건을 확인하고 README에서 상대 경로로 참조한다.
