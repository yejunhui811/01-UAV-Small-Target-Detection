# Evaluation policy

YOLO 첫 실행의 구체적인 evaluator·area·P/R·timing 규칙은 [baseline 안내](yolo-baseline.md)에 있다. 공식 VisDrone 평가와 구분한 converted target-only COCO AP를 사용한다. 아래는 후속 비교에서도 유지하거나 명시적으로 변경해야 할 공통 정책이다.

| Metric | Planned definition / required record |
| --- | --- |
| mAP50 | IoU 0.50에서의 AP를 class 평균. evaluator와 class 포함 규칙 기록 |
| mAP50-95 | IoU 0.50부터 0.95까지 0.05 간격의 AP 평균. evaluator 버전 기록 |
| AP_small | 작은 객체에 대한 AP. 면적 기준, 원본/resize 좌표계, IoU protocol 명시 |
| Precision / Recall | confidence, matching IoU, 집계 기준을 명시한 operating point |
| FPS | 명시한 처리 범위에서 실제 처리한 원본 frame 수 / 측정 시간 |
| latency | image 또는 batch당 시간(ms). batch size와 분포 요약 기준 명시 |

tiny/small 구간은 실험 전에 확정한다. 모델이 출력하는 metric을 정의 확인 없이 `AP_small`로 부르지 않는다. dataset 고유 평가 규칙과 COCO 방식 평가를 구분하고 변환·ignored label 정책을 기록한다.

속도 비교 시 동일 hardware/device, precision, input size, batch size, warm-up, 측정 횟수와 preprocessing/postprocessing/I/O 포함 범위를 맞춘다. GPU는 적절한 동기화 방식도 기록한다. tiled inference의 FPS는 tile 수가 아니라 원본 frame 기준으로 비교하고 tile merge 시간을 기록한다.

가설과 비교 변수, seed, split을 먼저 고정한다. failure cases는 객체 크기, 가림, 밀집도, miss/false positive 등으로 분류해 [실험 기록](../experiments/template.md)에 근거와 한계를 남긴다. 검증된 실제 output만 결과로 공개한다.
