"""Regression tests for experiment safety, original-pixel AP and matching."""

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uav_small_target.yolo_experiment import (
    box_iou, coco_ground_truth, coco_metrics, contained, failure_summary,
    load_config, select_records, write_json, progress_record, write_progress,
)


class ConfigurationTests(unittest.TestCase):
    def test_all_committed_configs_parse(self):
        for name in ("smoke", "pilot", "baseline", "baseline-mps"):
            cfg = load_config(ROOT / f"configs/yolo-{name}.toml")
            self.assertEqual(cfg["train"]["optimizer"], "SGD")

    def test_subset_sampling_is_deterministic_and_rejects_oversize(self):
        rows = [{"output_image": str(i)} for i in range(20)]
        self.assertEqual(select_records(rows, 5, 42), select_records(rows, 5, 42))
        self.assertNotEqual(select_records(rows, 5, 42), select_records(rows, 5, 43))
        self.assertEqual(len(select_records(rows, 0, 42)), 20)
        with self.assertRaises(ValueError):
            select_records(rows, 21, 42)

    def test_paths_cannot_escape_dataset(self):
        with self.assertRaises(ValueError):
            contained(ROOT, "../outside")
        with self.assertRaises(ValueError):
            contained(ROOT, "/tmp/outside")

    def test_progress_does_not_claim_completion_before_evaluation(self):
        progress = progress_record(50, 50, {"mAP": 0.3, "invalid": float("nan")})
        self.assertEqual(progress["status"], "running")
        self.assertEqual(progress["epoch_metrics"]["mAP"], 0.3)
        self.assertIsNone(progress["epoch_metrics"]["invalid"])
        self.assertEqual(progress["non_finite_metric_keys"], ["invalid"])
        with self.assertRaises(ValueError):
            progress_record(51, 50)

    def test_atomic_progress_replacement_produces_valid_json_without_temp_files(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            write_progress(run, progress_record(1, 50))
            write_progress(run, progress_record(2, 50))
            self.assertEqual(json.loads((run / "progress.json").read_text())["completed_epochs"], 2)
            self.assertEqual(sorted(p.name for p in run.iterdir()), ["progress.json"])

    def test_pilot_rejects_subsets_and_config_typo(self):
        content = (ROOT / "configs/yolo-pilot.toml").read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(content.replace("train_images = 0", "train_images = 4"))
            with self.assertRaisesRegex(ValueError, "full train and val"):
                load_config(path)
            path.write_text(content.replace("epochs = 1", "epoch = 1"))
            with self.assertRaisesRegex(ValueError, "missing train keys"):
                load_config(path)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional model dependency absent")
    def test_framework_numpy_scalars_can_be_recorded_without_nan(self):
        import json
        import numpy as np
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metric.json"
            write_json(path, {"class_id": np.int64(1), "ap": np.float32(0.5)})
            self.assertEqual(json.loads(path.read_text()), {"class_id": 1, "ap": 0.5})
            with self.assertRaises(ValueError):
                write_json(path, {"ap": np.float64(float("nan"))})


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        target = {"category": 1, "x": 10, "y": 20, "width": 10, "height": 10, "yolo": {}}
        ignored = {**target, "category": 0, "yolo": None}
        zero = {**target, "height": 0, "yolo": None}
        self.gt = coco_ground_truth([{"image_size": [100, 200], "output_image": "images/val/a.jpg",
                                      "rows": [target, ignored, zero]}], {0: "pedestrian", 1: "car"})
        self.pred = {"image_id": 1, "category_id": 1, "bbox": [10, 20, 10, 10], "score": 0.9}

    def test_ground_truth_preserves_original_area_and_excludes_non_targets(self):
        self.assertEqual(len(self.gt["annotations"]), 1)
        self.assertEqual(self.gt["annotations"][0]["area"], 100)
        self.assertEqual(self.gt["annotations"][0]["bbox"], [10, 20, 10, 10])

    def test_duplicate_prediction_matches_target_only_once(self):
        result = failure_summary(self.gt, [self.pred, self.pred])
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 1, 0))
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)

    def test_wrong_class_and_low_confidence_cannot_match(self):
        result = failure_summary(self.gt, [{**self.pred, "category_id": 2}, {**self.pred, "score": 0.1}])
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 1, 1))
        self.assertEqual(result["missed_small"], 1)
        self.assertIsNone(failure_summary(self.gt, [])["precision"])

    def test_touching_and_disjoint_boxes_have_zero_iou(self):
        self.assertEqual(box_iou([0, 0, 10, 10], [10, 0, 10, 10]), 0)
        self.assertEqual(box_iou([0, 0, 10, 10], [30, 0, 10, 10]), 0)
        self.assertEqual(box_iou([0, 0, 10, 10], [0, 0, 10, 10]), 1)

    @unittest.skipUnless(importlib.util.find_spec("pycocotools"), "optional YOLO evaluation dependency absent")
    def test_coco_perfect_and_empty_predictions_with_custom_maxdet(self):
        perfect = coco_metrics(self.gt, [self.pred], 500)
        self.assertAlmostEqual(perfect["mAP50-95"], 1)
        self.assertAlmostEqual(perfect["AP_small"], 1)
        self.assertIsNone(perfect["AP_large"])
        missed = coco_metrics(self.gt, [], 500)
        self.assertEqual(missed["AP_small"], 0)


if __name__ == "__main__":
    unittest.main()
