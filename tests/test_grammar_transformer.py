"""Tests for ASL grammar transformation."""

from __future__ import annotations

import pytest

from src.grammar_transformer import ASLGrammarTransformer, TransformResult


@pytest.fixture
def transformer() -> ASLGrammarTransformer:
    return ASLGrammarTransformer(language="asl")


class TestTimeMarkerFronting:
    def test_yesterday_moves_to_front(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I went to the store yesterday")
        assert result.text.startswith("YESTERDAY")

    def test_today_moves_to_front(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I eat lunch today")
        assert result.text.startswith("TODAY")

    def test_tomorrow_moves_to_front(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("We will go tomorrow")
        assert result.text.startswith("TOMORROW")

    def test_multiword_time_phrase(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I worked last week")
        assert result.text.startswith("LAST WEEK")

    def test_this_morning_phrase(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I had coffee this morning")
        assert result.text.startswith("THIS MORNING")

    def test_now_moves_to_front(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I am hungry now")
        assert result.text.startswith("NOW")


class TestFunctionWordDropping:
    def test_articles_dropped(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("The cat is big")
        assert "THE" not in result.text
        assert "A" not in result.text.split()

    def test_copulas_dropped(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("The cat is big")
        assert "IS" not in result.text.split()
        assert "CAT" in result.text
        assert "BIG" in result.text

    def test_prepositions_dropped(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I go to the store")
        assert "TO" not in result.text.split()
        assert "THE" not in result.text.split()

    def test_meaningful_words_kept(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("She likes coffee")
        assert "COFFEE" in result.text


class TestQuestionHandling:
    def test_wh_question_word_at_end(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("What is your name?")
        assert result.text.endswith("WHAT")
        assert result.is_question

    def test_where_question(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Where do you live?")
        assert result.text.endswith("WHERE")
        assert result.is_question

    def test_who_question(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Who is your teacher?")
        assert result.text.endswith("WHO")
        assert result.is_question

    def test_yes_no_question_flagged(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Are you hungry?")
        assert result.is_question
        assert "YOU" in result.text
        assert "HUNGRY" in result.text

    def test_how_question(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("How are you?")
        assert result.text.endswith("HOW")
        assert result.is_question


class TestNegation:
    def test_not_moves_to_end(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I do not like it")
        assert result.text.endswith("NOT")
        assert result.is_negation

    def test_contraction_expanded(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I don't like coffee")
        assert "NOT" in result.text
        assert result.is_negation

    def test_cant_expanded(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I can't go")
        assert "NOT" in result.text
        assert result.is_negation

    def test_wont_expanded(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I won't eat that")
        assert "NOT" in result.text

    def test_never_moves_to_end(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I never eat fish")
        assert result.text.endswith("NEVER")
        assert result.is_negation


class TestVerbNormalization:
    def test_irregular_past_tense(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I went home")
        assert "GO" in result.text
        assert "WENT" not in result.text

    def test_irregular_past_participle(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("She has eaten lunch")
        assert "EAT" in result.text

    def test_regular_ed_suffix(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I walked home")
        assert "WALK" in result.text

    def test_progressive_ing(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("She is running fast")
        assert "RUN" in result.text

    def test_third_person_s(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("He wants food")
        assert "WANT" in result.text


class TestCombined:
    def test_time_and_verb_normalization(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("I went to the store yesterday")
        assert result.text.startswith("YESTERDAY")
        assert "GO" in result.text
        assert "THE" not in result.text
        assert "TO" not in result.text.split()

    def test_negation_with_time(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Yesterday I didn't eat lunch")
        assert result.text.startswith("YESTERDAY")
        assert "NOT" in result.text
        assert result.is_negation

    def test_question_with_negation(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Why don't you like coffee?")
        assert result.is_question
        assert result.is_negation
        assert "NOT" in result.text

    def test_full_sentence_reorder(self, transformer: ASLGrammarTransformer) -> None:
        # "Tomorrow I will not go to the store" →
        # TOMORROW I GO STORE NOT
        result = transformer.transform("Tomorrow I will not go to the store")
        words = result.text.split()
        assert words[0] == "TOMORROW"
        assert "NOT" in words
        assert "STORE" in words


class TestEdgeCases:
    def test_empty_string(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("")
        assert result.text == ""

    def test_whitespace_only(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("   ")
        assert result.text == ""

    def test_single_word(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Hello")
        assert result.text == "HELLO"

    def test_non_asl_language_passthrough(self) -> None:
        bsl_transformer = ASLGrammarTransformer(language="bsl")
        result = bsl_transformer.transform("I went to the store yesterday")
        assert result.text == "I went to the store yesterday"

    def test_result_is_uppercase(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("hello world")
        assert result.text == result.text.upper()

    def test_punctuation_stripped(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Hello!")
        assert "!" not in result.text

    def test_only_function_words(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("the a an is")
        assert result.text == ""

    def test_returns_transform_result(self, transformer: ASLGrammarTransformer) -> None:
        result = transformer.transform("Hello")
        assert isinstance(result, TransformResult)
        assert isinstance(result.is_question, bool)
        assert isinstance(result.is_negation, bool)
