# Experiment: <experiment-id>

Status: planned — not executed. 아래 항목은 미기입 양식이며 실험 결과가 아니다.

## Hypothesis and comparison
- Hypothesis:
- Research question:
- Control/baseline experiment ID:
- Changed variable and fixed conditions:
- Criteria for interpreting the outcome:

## Model and dataset
- Model family / variant / implementation version:
- Pretrained weights source / version / SHA-256:
- Dataset release / provenance / local root:
- Train / validation / test splits and overlap checks:
- Dataset manifest checksum / class mapping / annotation conversion version:
- Ignored annotations and tiny/small definition / coordinate space:

## Configuration and execution
- Experiment configuration path:
- Git branch / exact commit / working tree clean or dirty:
- Seed(s) / deterministic settings / known nondeterminism:
- Exact command (including working directory):
- Start / end time with timezone:
- Output directory / external artifact location / checksums:

## Environment
- OS / Python version / package versions:
- Dependency snapshot path (review for credentials before sharing):
- CPU / GPU / memory / CUDA and driver versions:
- Device / precision / batch size / input resolution:
- Tiling and augmentation settings:

## Measurement protocol
- Evaluator name / version / IoU protocol / class averaging:
- AP_small and any custom tiny bins: area thresholds / coordinate space:
- Precision/Recall: confidence and matching thresholds:
- Timing: warm-up / iterations / I/O and preprocessing/postprocessing scope:
- Device synchronization / repetition count / variability:

## Metrics
Not measured. 실제 output에서 확인한 후에만 표를 채운다.

| Metric | Measured value | Unit / definition | Evidence path |
| --- | --- | --- | --- |
| mAP50 | | | |
| mAP50-95 | | | |
| AP_small | | | |
| Precision | | | |
| Recall | | | |
| FPS | | frames/s | |
| latency | | ms/image or ms/batch (specify) | |

## Result and analysis
- Result:
- Comparison to hypothesis and baseline:
- Limitations / variability / confounders:

## Failure cases
- Sample identifier (without committing raw dataset media):
- Failure category (miss, false positive, localization, class confusion, etc.):
- Object size / occlusion / crowding / relevant conditions:
- Prediction evidence location and sharing permission:
- Possible cause and follow-up experiment:

## Conclusion
- Supported / unsupported / inconclusive hypothesis:
- Next step:
