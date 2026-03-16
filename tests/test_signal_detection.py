"""
Tests for signal detection functions in update_jobs.py.

These tests verify the new_grad_signal and track_signal detection functions,
which are used to identify job titles containing relevant keywords.
"""

import sys
import os

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_jobs import has_new_grad_signal, has_track_signal


class TestHasNewGradSignal:
    """Tests for has_new_grad_signal() function."""

    def test_exact_match_single_signal(self):
        """Test exact match with a single signal keyword."""
        signals = ['graduate', 'entry-level', 'junior']
        # Note: 'entry-level' is a substring match, so 'entry level' (with space) won't match
        assert has_new_grad_signal('Software Engineer - Junior', signals) is True

    def test_exact_match_case_insensitive(self):
        """Test that signal matching is case-insensitive."""
        signals = ['graduate', 'entry-level']
        assert has_new_grad_signal('Software Engineer - ENTRY-LEVEL', signals) is True
        assert has_new_grad_signal('software ENGINEER - entry-level', signals) is True
        assert has_new_grad_signal('GRADUATE ENGINEER', signals) is True

    def test_no_match_returns_false(self):
        """Test that non-matching titles return False."""
        signals = ['graduate', 'entry-level', 'junior']
        assert has_new_grad_signal('Senior Software Engineer', signals) is False
        assert has_new_grad_signal('Staff Engineer', signals) is False
        assert has_new_grad_signal('Principal Architect', signals) is False

    def test_partial_match_within_word(self):
        """Test that signal is found within words (substring match)."""
        signals = ['grad']
        assert has_new_grad_signal('Graduate Program', signals) is True
        assert has_new_grad_signal('Post-Graduate Fellowship', signals) is True

    def test_multiple_signals_first_matches(self):
        """Test with multiple signals, first one matches."""
        signals = ['graduate', 'entry-level', 'junior']
        assert has_new_grad_signal('New Graduate Position', signals) is True

    def test_multiple_signals_middle_matches(self):
        """Test with multiple signals, middle one matches."""
        signals = ['graduate', 'entry-level', 'junior']
        # 'entry-level' with hyphen must match exactly in title
        assert has_new_grad_signal('Entry-Level Software Engineer', signals) is True

    def test_multiple_signals_last_matches(self):
        """Test with multiple signals, last one matches."""
        signals = ['graduate', 'entry-level', 'junior']
        assert has_new_grad_signal('Junior Developer', signals) is True

    def test_empty_signals_list(self):
        """Test with empty signals list."""
        assert has_new_grad_signal('Graduate Engineer', []) is False

    def test_empty_title(self):
        """Test with empty title string."""
        signals = ['graduate', 'entry-level']
        assert has_new_grad_signal('', signals) is False

    def test_whitespace_handling(self):
        """Test that signals match with various whitespace."""
        signals = ['entry level']
        assert has_new_grad_signal('Entry Level Software Engineer', signals) is True
        assert has_new_grad_signal('entry-level', signals) is False  # no space

    def test_unicode_characters(self):
        """Test with unicode characters in title and signals."""
        signals = ['新卒', 'エントリー']  # Japanese characters
        assert has_new_grad_signal('新卒エンジニア', signals) is True

    def test_signal_at_start(self):
        """Test signal at the beginning of title."""
        signals = ['junior']
        assert has_new_grad_signal('Junior Software Engineer', signals) is True

    def test_signal_at_end(self):
        """Test signal at the end of title."""
        signals = ['track']
        assert has_new_grad_signal('Software Engineering Track', signals) is True

    def test_signal_in_middle(self):
        """Test signal in the middle of title."""
        signals = ['graduate']
        assert has_new_grad_signal('New Graduate Program Engineer', signals) is True

    def test_single_signal_as_entire_title(self):
        """Test when signal equals entire title."""
        signals = ['graduate']
        assert has_new_grad_signal('graduate', signals) is True

    def test_very_long_title(self):
        """Test with a very long job title."""
        signals = ['junior']
        long_title = 'Junior ' + 'Software Engineer ' * 50 + 'Position'
        assert has_new_grad_signal(long_title, signals) is True

    def test_special_characters_in_signal(self):
        """Test signals with special characters."""
        signals = ['entry-level', 'co-op', 'u+1']
        assert has_new_grad_signal('Entry-Level Position', signals) is True
        assert has_new_grad_signal('Co-Op Role', signals) is True


class TestHasTrackSignal:
    """Tests for has_track_signal() function."""

    def test_exact_match_single_signal(self):
        """Test exact match with a single signal keyword."""
        signals = ['software', 'data', 'backend']
        assert has_track_signal('Software Engineer', signals) is True

    def test_exact_match_case_insensitive(self):
        """Test that signal matching is case-insensitive."""
        signals = ['software', 'data']
        assert has_track_signal('SOFTWARE ENGINEER', signals) is True
        assert has_track_signal('Data Scientist', signals) is True
        assert has_track_signal('software engineer', signals) is True

    def test_no_match_returns_false(self):
        """Test that non-matching titles return False."""
        signals = ['software', 'data', 'backend']
        assert has_track_signal('Hardware Engineer', signals) is False
        assert has_track_signal('Sales Manager', signals) is False

    def test_partial_match_within_word(self):
        """Test that signal is found within words (substring match)."""
        signals = ['soft']
        assert has_track_signal('Software Engineer', signals) is True
        assert has_track_signal('Softwire Developer', signals) is True

    def test_multiple_signals_all_checked(self):
        """Test with multiple signals to ensure all are checked."""
        signals = ['software', 'data', 'infrastructure']
        assert has_track_signal('Software Engineer', signals) is True
        assert has_track_signal('Data Engineer', signals) is True
        assert has_track_signal('Infrastructure Manager', signals) is True

    def test_empty_signals_list(self):
        """Test with empty signals list."""
        assert has_track_signal('Software Engineer', []) is False

    def test_empty_title(self):
        """Test with empty title string."""
        signals = ['software', 'data']
        assert has_track_signal('', signals) is False

    def test_common_track_keywords(self):
        """Test with common job track keywords."""
        signals = ['software', 'data', 'backend', 'frontend', 'mobile']
        assert has_track_signal('Backend Software Engineer', signals) is True
        assert has_track_signal('Mobile Developer', signals) is True
        assert has_track_signal('Frontend React Engineer', signals) is True
        assert has_track_signal('Data Analytics Engineer', signals) is True

    def test_signal_variations(self):
        """Test that signal variations require exact substring match."""
        signals = ['data']
        assert has_track_signal('Data Engineer', signals) is True
        assert has_track_signal('Databases', signals) is True  # substring match
        assert has_track_signal('Update', signals) is False

    def test_unicode_characters(self):
        """Test with unicode characters in title and signals."""
        signals = ['ソフトウェア', 'データ']  # Japanese characters
        assert has_track_signal('ソフトウェアエンジニア', signals) is True
        assert has_track_signal('データサイエンティスト', signals) is True

    def test_signal_at_various_positions(self):
        """Test signals at start, middle, and end of title."""
        signals = ['backend']
        assert has_track_signal('Backend Engineer', signals) is True
        assert has_track_signal('Senior Backend Engineer', signals) is True
        assert has_track_signal('Backend Development Manager', signals) is True

    def test_with_hyphenated_keywords(self):
        """Test with hyphenated track keywords."""
        signals = ['full-stack', 'web-based']
        assert has_track_signal('Full-Stack Engineer', signals) is True
        assert has_track_signal('Web-Based Developer', signals) is True

    def test_with_numbers_in_title(self):
        """Test with numbers in job title."""
        signals = ['software', 'level3']
        assert has_track_signal('Software Engineer Level 3', signals) is True
        assert has_track_signal('Level 3 Software Engineer', signals) is True
        assert has_track_signal('Level3 Engineer', signals) is True  # 'level3' substring matches

    def test_very_long_signal_list(self):
        """Test with a large number of signals."""
        signals = ['track' + str(i) for i in range(100)]
        signals.append('data')
        assert has_track_signal('Data Engineer Track', signals) is True

    def test_single_character_signal(self):
        """Test with single-character signal."""
        signals = ['I']  # Capital I as a signal
        assert has_track_signal('I-Team Engineer', signals) is True
        assert has_track_signal('Information', signals) is True


class TestSignalDetectionSemantics:
    """Integration tests verifying signal detection semantics."""

    def test_both_signal_types_on_same_title(self):
        """Test that both signal types can match on same title."""
        new_grad_signals = ['graduate', 'entry-level']
        track_signals = ['software']
        title = 'Entry-Level Software Engineer Graduate'
        assert has_new_grad_signal(title, new_grad_signals) is True
        assert has_track_signal(title, track_signals) is True

    def test_distinct_signal_types_dont_interfere(self):
        """Test that one type of signal doesn't affect the other."""
        new_grad_signals = ['graduate']
        track_signals = ['data']
        title = 'Data Scientist'
        assert has_new_grad_signal(title, new_grad_signals) is False
        assert has_track_signal(title, track_signals) is True

    def test_filtering_with_both_signals(self):
        """Test realistic filtering scenario with both signal types."""
        jobs = [
            {'title': 'Senior Software Engineer'},
            {'title': 'Entry-Level Software Engineer'},
            {'title': 'Graduate Data Scientist'},
            {'title': 'Hardware Specialist'},
        ]
        new_grad_signals = ['graduate', 'entry-level']
        track_signals = ['software', 'data']

        new_grad_and_track = [
            j for j in jobs
            if has_new_grad_signal(j['title'], new_grad_signals) and
               has_track_signal(j['title'], track_signals)
        ]
        assert len(new_grad_and_track) == 2  # Entry-Level SW and Graduate Data
        assert new_grad_and_track[0]['title'] == 'Entry-Level Software Engineer'
        assert new_grad_and_track[1]['title'] == 'Graduate Data Scientist'
