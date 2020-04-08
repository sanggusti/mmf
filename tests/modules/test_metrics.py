# Copyright (c) Facebook, Inc. and its affiliates.
import os
import unittest

import torch
import yaml

import pythia.modules.metrics as metrics
from pythia.common.registry import registry
from pythia.common.sample import Sample
from pythia.datasets.processors import CaptionProcessor
from pythia.utils.configuration import load_yaml


class TestModuleMetrics(unittest.TestCase):
    def test_caption_bleu4(self):
        path = os.path.join(
            os.path.abspath(__file__),
            "../../../pythia/configs/datasets/coco/defaults.yaml",
        )
        config = load_yaml(os.path.abspath(path))
        captioning_config = config.dataset_config.coco
        caption_processor_config = captioning_config.processors.caption_processor
        vocab_path = os.path.join(
            os.path.abspath(__file__), "..", "..", "data", "vocab.txt"
        )
        caption_processor_config.params.vocab.type = "random"
        caption_processor_config.params.vocab.vocab_file = os.path.abspath(vocab_path)
        caption_processor = CaptionProcessor(caption_processor_config.params)
        registry.register("coco_caption_processor", caption_processor)

        caption_bleu4 = metrics.CaptionBleu4Metric()
        expected = Sample()
        predicted = dict()

        # Test complete match
        expected.answers = torch.empty((5, 5, 10))
        expected.answers.fill_(4)
        predicted["scores"] = torch.zeros((5, 10, 19))
        predicted["scores"][:, :, 4] = 1.0

        self.assertEqual(caption_bleu4.calculate(expected, predicted).item(), 1.0)

        # Test partial match
        expected.answers = torch.empty((5, 5, 10))
        expected.answers.fill_(4)
        predicted["scores"] = torch.zeros((5, 10, 19))
        predicted["scores"][:, 0:5, 4] = 1.0
        predicted["scores"][:, 5:, 18] = 1.0

        self.assertAlmostEqual(
            caption_bleu4.calculate(expected, predicted).item(), 0.3928, 4
        )

    def _test_binary_metric(self, metric, value):
        sample = Sample()
        predicted = dict()

        sample.targets = torch.tensor(
            [[0, 1], [1, 0], [1, 0], [0, 1]], dtype=torch.float
        )
        predicted["scores"] = torch.tensor(
            [
                [-0.9332, 0.8149],
                [-0.8391, 0.6797],
                [-0.7235, 0.7220],
                [-0.9043, 0.3078],
            ],
            dtype=torch.float,
        )
        self.assertAlmostEqual(metric.calculate(sample, predicted).item(), value, 4)

        sample.targets = torch.tensor([1, 0, 0, 1], dtype=torch.long)
        self.assertAlmostEqual(metric.calculate(sample, predicted).item(), value, 4)

    def _test_multiclass_metric(self, metric, value):
        sample = Sample()
        predicted = dict()

        sample.targets = torch.tensor(
            [[0, 1, 0], [0, 0, 1], [1, 0, 0], [0, 0, 1]], dtype=torch.float
        )
        predicted["scores"] = torch.tensor(
            [
                [-0.9332, 0.8149, 0.3491],
                [-0.8391, 0.6797, -0.3410],
                [-0.7235, 0.7220, 0.9104],
                [0.9043, 0.3078, -0.4210],
            ],
            dtype=torch.float,
        )
        self.assertAlmostEqual(metric.calculate(sample, predicted).item(), value, 4)

        sample.targets = torch.tensor([1, 2, 0, 2], dtype=torch.long)
        self.assertAlmostEqual(metric.calculate(sample, predicted).item(), value, 4)

    def _test_multilabel_metric(self, metric, value):
        sample = Sample()
        predicted = dict()

        sample.targets = torch.tensor(
            [[0, 1, 1], [1, 0, 1], [1, 0, 1], [0, 0, 1]], dtype=torch.float
        )
        predicted["scores"] = torch.tensor(
            [
                [-0.9332, 0.8149, 0.3491],
                [-0.8391, 0.6797, -0.3410],
                [-0.7235, 0.7220, 0.9104],
                [0.9043, 0.3078, -0.4210],
            ],
            dtype=torch.float,
        )
        self.assertAlmostEqual(metric.calculate(sample, predicted).item(), value, 4)

    def test_micro_f1(self):
        metric = metrics.MicroF1()
        self._test_binary_metric(metric, 0.5)
        self._test_multiclass_metric(metric, 0.25)

    def test_macro_f1(self):
        metric = metrics.MacroF1()
        self._test_binary_metric(metric, 0.3333)
        self._test_multiclass_metric(metric, 0.2222)

    def test_binary_f1(self):
        metric = metrics.BinaryF1()
        self._test_binary_metric(metric, 0.66666666)

    def test_multilabel_micro_f1(self):
        metric = metrics.MultiLabelMicroF1()
        self._test_binary_metric(metric, 0.5)

    def test_multilabel_macro_f1(self):
        metric = metrics.MultiLabelMacroF1()
        self._test_multilabel_metric(metric, 0.13333)

    def test_macro_roc_auc(self):
        metric = metrics.MacroROC_AUC()
        self._test_binary_metric(metric, 0.5)
        self._test_multiclass_metric(metric, 0.2222)

    def test_micro_roc_auc(self):
        metric = metrics.MicroROC_AUC()
        self._test_binary_metric(metric, 0.5)
        self._test_multiclass_metric(metric, 0.34375)

    def test_micro_ap(self):
        metric = metrics.MicroAP()
        self._test_binary_metric(metric, 0.5)
        self._test_multiclass_metric(metric, 0.34375)

    def test_macro_ap(self):
        metric = metrics.MacroAP()
        self._test_binary_metric(metric, 0.5)
        self._test_multiclass_metric(metric, 0.2222)
