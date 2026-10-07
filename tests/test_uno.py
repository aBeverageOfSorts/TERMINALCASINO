"""
Unit testing for UNO stat tracking and the post-game stats screen
(casino/games/uno/player.py, uno.py, and views/view.py)
"""

import unittest
from unittest.mock import patch

from casino.cards import UnoCard
from casino.games.uno.player import Player
from casino.games.uno.uno import Uno
from casino.games.uno.views.view import (
    format_player_page,
    format_summary_table,
    next_page_index,
)


def make_deck(*specs):
    """Build a list of UnoCards from (color, rank) tuples."""
    return [UnoCard(color, rank) for color, rank in specs]


class TestPlayerDrawStats(unittest.TestCase):
    def setUp(self):
        self.player = Player(0, "alice")
        self.deck = make_deck(*[("red", str(n)) for n in range(10)])

    def test_voluntary_draw_counts_once(self):
        self.player.draw(self.deck)
        self.assertEqual(self.player.draws_taken, 1)
        self.assertEqual(len(self.player.hand), 1)

    def test_deal_is_not_a_draw(self):
        for _ in range(7):
            self.player.draw(self.deck, reason="deal")
        self.assertEqual(self.player.draws_taken, 0)
        self.assertEqual(self.player.penalty_cards, 0)
        self.assertEqual(len(self.player.hand), 7)

    def test_penalty_cards_tracked_separately(self):
        for _ in range(4):
            self.player.draw(self.deck, reason="penalty")
        self.assertEqual(self.player.penalty_cards, 4)
        self.assertEqual(self.player.draws_taken, 0)

    def test_unknown_reason_raises(self):
        with self.assertRaises(ValueError):
            self.player.draw(self.deck, reason="oops")


class TestPlayerPlayStats(unittest.TestCase):
    def test_each_action_card_updates_its_counter(self):
        player = Player(0, "bob")
        player.hand = make_deck(
            ("red", "5"), ("red", "draw_2"), ("red", "skip"),
            ("red", "reverse"), ("wild", "wild"), ("wild", "wild_draw_4"),
        )
        for card in list(player.hand):
            player.play_card(card)

        self.assertEqual(player.cards_played, 6)
        self.assertEqual(player.draw2_played, 1)
        self.assertEqual(player.skips_played, 1)
        self.assertEqual(player.reverses_played, 1)
        self.assertEqual(player.wilds_played, 1)
        self.assertEqual(player.draw4_played, 1)
        self.assertEqual(player.hand, [])


class FakeView:
    """Stands in for UnoView: feeds scripted answers and records the winner."""

    def __init__(self, actions, cards):
        self.actions = iter(actions)
        self.cards = iter(cards)
        self.winner = None

    def prompt_num_players(self):
        return 1

    def prompt_player_name(self, i):
        return "tester"

    def prompt_draw_or_play(self):
        return next(self.actions)

    def prompt_which_card(self):
        return next(self.cards)

    def show_winner(self, winner, players):
        self.winner = winner

    def __getattr__(self, name):
        # every other view method (display_topbar, show_turn, ...) is a no-op
        return lambda *args, **kwargs: None


class TestUnoGameStats(unittest.TestCase):
    def test_full_game_stats_are_accurate(self):
        """
        One scripted game: the player is dealt 7 cards, draws once,
        then plays all 8 cards (including a skip and a reverse) to win.
        Before the fix, draws_taken was 9 (7 dealt + the draw counted twice)
        and the skip/reverse counters stayed at 0.
        """
        deck = make_deck(
            ("red", "1"), ("red", "2"), ("red", "3"), ("red", "4"),
            ("red", "5"), ("red", "skip"), ("red", "reverse"),  # dealt hand
            ("red", "0"),                                       # first discard
            ("red", "6"),                                       # drawn card
            ("blue", "9"), ("blue", "8"),                       # spare cards
        )

        class FakeDeck:
            def __init__(self):
                self.cards = deck

        view = FakeView(
            actions=["d"] + ["p"] * 8,
            cards=["red 1", "red 2", "red 3", "red 4", "red 5",
                   "red skip", "red reverse", "red 6"],
        )

        first_card = lambda seq: seq[0]  # make "random" draws deterministic
        with patch("casino.games.uno.uno.UnoDeck", FakeDeck), \
             patch("casino.games.uno.uno.random.choice", first_card), \
             patch("casino.games.uno.player.random.choice", first_card):
            game = Uno(ctx=None)
            game.view = view
            game.play_uno()

        p = view.winner
        self.assertIsNotNone(p)
        self.assertEqual(p.hand, [])
        self.assertEqual(p.draws_taken, 1)
        self.assertEqual(p.cards_played, 8)
        self.assertEqual(p.skips_played, 1)
        self.assertEqual(p.reverses_played, 1)
        self.assertEqual(p.penalty_cards, 0)


class TestStatsScreen(unittest.TestCase):
    def setUp(self):
        self.alice = Player(0, "alice")
        self.bob = Player(1, "bob")
        self.alice.cards_played = 12
        self.bob.penalty_cards = 4
        self.bob.hand = make_deck(("red", "1"), ("blue", "2"))

    def test_summary_table_has_a_row_per_player(self):
        table = format_summary_table([self.alice, self.bob])
        self.assertIn("ALICE", table)
        self.assertIn("BOB", table)
        self.assertIn("Penalty", table)

    def test_player_page_marks_winner(self):
        page = format_player_page(self.alice, self.alice, 0, 2)
        self.assertIn("WINNER", page)
        self.assertIn("12", page)

    def test_player_page_for_non_winner(self):
        page = format_player_page(self.bob, self.alice, 1, 2)
        self.assertNotIn("WINNER", page)
        self.assertIn("player 2 of 2", page)

    def test_page_navigation_wraps(self):
        self.assertEqual(next_page_index(0, "n", 3), 1)
        self.assertEqual(next_page_index(2, "n", 3), 0)
        self.assertEqual(next_page_index(0, "p", 3), 2)
        self.assertEqual(next_page_index(1, "x", 3), 1)


if __name__ == "__main__":
    unittest.main()
