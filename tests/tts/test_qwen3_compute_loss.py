"""Tests for Qwen3VoiceTrainer._compute_loss pattern matching.

Uses plain Python MagicMock objects to simulate the various return
shapes Qwen3-TTS forward could produce. MLX tensor arithmetic is
stubbed via a simple float/Mock sentinel so tests run without MLX/
mlx-audio installed — matches how the factory is used on non-Apple
CI machines.
"""

from unittest.mock import MagicMock

import pytest

# Skip the entire file if MLX is not available — _compute_loss imports it
mlx = pytest.importorskip("mlx.core")

from saymo.tts.qwen3_trainer import Qwen3VoiceTrainer


def test_dict_with_loss_key():
    model = MagicMock(return_value={"loss": 1.23})
    result = Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")
    assert result == 1.23


def test_object_with_loss_attr():
    output = MagicMock()
    output.loss = 2.5
    # Make sure it's not caught by the dict branch
    del output.__class__.__iter__  # pragma: no cover
    model = MagicMock(return_value=output)
    result = Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")
    assert result == 2.5


def test_unsupported_shape_raises():
    # Plain dict without loss / logits → should raise with descriptive message
    model = MagicMock(return_value={"something": 42})
    with pytest.raises(NotImplementedError, match="unsupported shape"):
        Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")


def test_unsupported_scalar_raises():
    model = MagicMock(return_value=0.5)
    with pytest.raises(NotImplementedError, match="unsupported shape"):
        Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")


def test_logits_labels_dict_branch_reached():
    """When dict has logits+labels, cross_entropy is called and returned."""
    import mlx.core as mx_mod
    import mlx.nn as nn_mod

    logits = mx_mod.array([[1.0, 2.0, 3.0], [0.5, 0.3, 0.2]])
    labels = mx_mod.array([2, 0])

    model = MagicMock(return_value={"logits": logits, "labels": labels})
    result = Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")

    expected = nn_mod.losses.cross_entropy(logits, labels, reduction="mean")
    assert float(result) == pytest.approx(float(expected))


def test_logits_labels_tuple_branch_reached():
    """Same as above but for tuple output."""
    import mlx.core as mx_mod
    import mlx.nn as nn_mod

    logits = mx_mod.array([[0.1, 0.9], [0.8, 0.2]])
    labels = mx_mod.array([1, 0])

    model = MagicMock(return_value=(logits, labels))
    result = Qwen3VoiceTrainer._compute_loss(model, "hi", "x.wav")

    expected = nn_mod.losses.cross_entropy(logits, labels, reduction="mean")
    assert float(result) == pytest.approx(float(expected))
