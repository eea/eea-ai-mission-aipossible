from pathlib import Path

import pytest

from analysis.clients.base import BaseAIClient


class DummyClient(BaseAIClient):
    def analyze(self, text: str) -> dict:
        return {"result": text}


def _write_prompts(tmp_path: Path, user_prompt: str) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "system_prompt.txt").write_text("System prompt", encoding="utf-8")
    (prompts_dir / "user_prompt.txt").write_text(user_prompt, encoding="utf-8")
    return prompts_dir


def test_generates_response_format_from_digit_count(tmp_path: Path) -> None:
    user_prompt = "I would like you to analyse the following 10 questions.\n\n{INSERT SCRAPED TEXT HERE}"
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    assert '"Answer 1": ""' in client.response_format
    assert '"Answer 10": ""' in client.response_format
    assert '"Answer 11": ""' not in client.response_format


def test_generates_response_format_from_word_count(tmp_path: Path) -> None:
    user_prompt = "I would like you to analyse the following ten questions.\n\n{INSERT SCRAPED TEXT HERE}"
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    assert '"Answer 10": ""' in client.response_format


def test_parses_alternate_phrase_with_following_count(tmp_path: Path) -> None:
    user_prompt = "I would like you to give me answers to the following 3 questions.\n\n{INSERT SCRAPED TEXT HERE}"
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    assert '"Answer 3": ""' in client.response_format
    assert '"Answer 4": ""' not in client.response_format


def test_parses_count_statement_beyond_first_20_lines(tmp_path: Path) -> None:
    intro = "\n".join(f"line {index}" for index in range(1, 22))
    user_prompt = (
        f"{intro}\nI would like you to analyse the following 4 questions.\n\n"
        "{INSERT SCRAPED TEXT HERE}"
    )
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)
    assert '"Answer 4": ""' in client.response_format
    assert '"Answer 5": ""' not in client.response_format


def test_parses_count_statement_with_questions_below_phrase(tmp_path: Path) -> None:
    user_prompt = (
        "Analyze the above-mentioned response and answer the 3 questions below.\n\n"
        "{INSERT SCRAPED TEXT HERE}"
    )
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    assert '"Answer 3": ""' in client.response_format
    assert '"Answer 4": ""' not in client.response_format


def test_raises_when_count_statement_missing(tmp_path: Path) -> None:
    user_prompt = "Please analyze this text.\n\n{INSERT SCRAPED TEXT HERE}"
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    with pytest.raises(ValueError, match="Could not determine question count"):
        DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)


def test_raises_for_zero_or_unsupported_number(tmp_path: Path) -> None:
    user_prompt_zero = "I would like you to analyse the following 0 questions."
    prompts_dir_zero = _write_prompts(tmp_path / "zero", user_prompt_zero)
    with pytest.raises(ValueError, match="positive integer"):
        DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir_zero, user_prompt_template=user_prompt_zero)

    user_prompt_word = "I would like you to analyse the following many questions."
    prompts_dir_word = _write_prompts(tmp_path / "word", user_prompt_word)
    with pytest.raises(ValueError, match="Unsupported number word"):
        DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir_word, user_prompt_template=user_prompt_word)


def test_generated_rules_block_matches_required_text(tmp_path: Path) -> None:
    user_prompt = "I would like you to analyse the following 2 questions.\n\n{INSERT SCRAPED TEXT HERE}"
    prompts_dir = _write_prompts(tmp_path, user_prompt)

    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    assert "Return ONLY valid JSON. Use this exact schema with string values:" in client.response_format
    assert "Rules:" in client.response_format
    assert "- Do not include any text outside the JSON." in client.response_format
    assert "- Keep the keys exactly as shown." in client.response_format
    assert "- Each value must be a string." in client.response_format
    assert '- Use "" when the answer is missing.' in client.response_format


def test_auto_appends_text_to_analyse_block_when_missing(tmp_path: Path) -> None:
    user_prompt = "I would like you to analyse the following 2 questions."
    prompts_dir = _write_prompts(tmp_path, user_prompt)
    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    rendered = client._render_user_prompt("sample text")
    assert "Response text:" in rendered
    assert "<<<\nsample text\n>>>" in rendered
    assert rendered.index("Response text:") < rendered.index("I would like you to analyse")


def test_normalizes_row_text_placeholder(tmp_path: Path) -> None:
    user_prompt = "Analyze the response and answer the 3 questions below.\n\nResponse text:\n<<<\n{ROW_TEXT}\n>>>"
    prompts_dir = _write_prompts(tmp_path, user_prompt)
    client = DummyClient(api_key="", model="m", api_url="", prompts_dir=prompts_dir, user_prompt_template=user_prompt)

    rendered = client._render_user_prompt("sample text")
    assert "{ROW_TEXT}" not in client.user_prompt_template
    assert "{INSERT SCRAPED TEXT HERE}" in client.user_prompt_template
    assert "<<<\nsample text\n>>>" in rendered


def test_constructor_override_prompt_is_used_and_block_not_duplicated(tmp_path: Path) -> None:
    prompts_dir = _write_prompts(
        tmp_path,
        "I would like you to analyse the following 2 questions.\n\n{INSERT SCRAPED TEXT HERE}",
    )
    override_prompt = "I would like you to analyse the following 3 questions."
    client = DummyClient(
        api_key="",
        model="m",
        api_url="",
        prompts_dir=prompts_dir,
        user_prompt_template=override_prompt,
    )

    rendered = client._render_user_prompt("abc")
    assert '"Answer 3": ""' in client.response_format
    assert '"Answer 4": ""' not in client.response_format
    assert rendered.count("Response text:") == 1
    assert rendered.index("Response text:") < rendered.index("I would like you to analyse")
