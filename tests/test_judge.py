from unittest.mock import MagicMock, patch

import anthropic
import pytest

from transfer_court.judge import JudgeError, extract_score, judge_output


def test_extract_score_from_clean_json():
    assert extract_score('Looks good. {"score": 4}') == 4


def test_extract_score_clamps_to_valid_range():
    assert extract_score('{"score": 99}') == 5  # clamped to max


def test_extract_score_falls_back_to_zero_on_garbage():
    assert extract_score("no json here at all") == 0


@patch("transfer_court.judge.anthropic.Anthropic")
def test_judge_output_is_blind_to_arm_label(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='Meets obligation. {"score": 4}')]
    mock_client.messages.create.return_value = mock_response

    score, raw = judge_output(obligation="the code adds two numbers", output="def add(a,b): return a+b")

    sent_prompt = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "arm" not in sent_prompt.lower()
    assert "panel" not in sent_prompt.lower()
    assert score == 4


@patch("transfer_court.judge.time.sleep")
@patch("transfer_court.judge.anthropic.Anthropic")
def test_judge_output_raises_after_retryable_errors_exhausted(mock_anthropic_cls, mock_sleep):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    connection_error = anthropic.APIConnectionError(request=MagicMock())
    mock_client.messages.create.side_effect = connection_error

    with pytest.raises(JudgeError, match="after 3 attempts"):
        judge_output(obligation="x", output="y")

    assert mock_client.messages.create.call_count == 3


@patch("transfer_court.judge.anthropic.Anthropic")
def test_judge_output_raises_immediately_on_non_retryable_error(mock_anthropic_cls):
    # A malformed response shape (or any error that isn't a transient
    # network/service condition) should not be retried 3 times — it will
    # fail the same way every time.
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.side_effect = ValueError("unexpected response shape")

    with pytest.raises(JudgeError, match="judge call failed"):
        judge_output(obligation="x", output="y")

    assert mock_client.messages.create.call_count == 1
