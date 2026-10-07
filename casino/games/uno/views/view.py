from casino.utils import clear_screen, cprint, cinput, display_topbar

UNO_HEADER = """
┌───────────────────────────────┐
│             UNO!              │
└───────────────────────────────┘
"""

DRAW_PROMPT = "Would you like to: [D]raw a card or [P]lay a card?"
WHICH_CARD_PROMPT1 = "Which card would you like to play?\n"
WHICH_CARD_PROMPT2 = "Enter card suite and number. Ex: \"red 2\", \"red skip\", \"red reverse\", \"red +2\""
WHICH_CARD_PROMPT3 = "For special cards, only enter \"+4\" or \"wild\""
INVALID_CARD_MSG = "You can't play that card! Enter 'draw' if you would like to draw a card, otherwise press enter to select another card."

QUIT_KEYS = {"q", "quit"}

#(label, attribute on Player) for every tracked stat, in display order
PLAYER_STATS = [
    ("Cards played", "cards_played"),
    ("Cards drawn", "draws_taken"),
    ("Penalty cards taken", "penalty_cards"),
    ("+2 played", "draw2_played"),
    ("Skips played", "skips_played"),
    ("Reverses played", "reverses_played"),
    ("Wilds played", "wilds_played"),
    ("+4 played", "draw4_played"),
]


def format_summary_table(players) -> str:
    """Return a table with one row of stats per player."""
    header = f"{'Player':<12} {'Left':>4} {'Played':>6} {'Drawn':>5} {'Penalty':>7} {'+2':>3} {'Skip':>4} {'Rev':>3} {'Wild':>4} {'+4':>3}"
    lines = ["FINAL STATISTICS", "═" * len(header), header, "─" * len(header)]
    for p in players:
        lines.append(
            f"{p.name[:12]:<12} {len(p.hand):>4} {p.cards_played:>6} {p.draws_taken:>5} "
            f"{p.penalty_cards:>7} {p.draw2_played:>3} {p.skips_played:>4} "
            f"{p.reverses_played:>3} {p.wilds_played:>4} {p.draw4_played:>3}"
        )
    lines.append("═" * len(header))
    return "\n".join(lines)


def format_player_page(player, winner, index: int, total: int) -> str:
    """Return the detailed stats page for a single player."""
    title = f"{player.name}  (player {index + 1} of {total})"
    if player is winner:
        title += "  ★ WINNER"
    rows = [("Cards left in hand", len(player.hand))]
    rows += [(label, getattr(player, attr)) for label, attr in PLAYER_STATS]

    width = max(len(title), 36)  # fixed width so every page lines up
    lines = [title, "─" * width]
    for label, value in rows:
        lines.append(f"{label + ':':<24}{value:>{width - 24}}")
    lines.append("─" * width)
    return "\n".join(lines)


def next_page_index(index: int, key: str, total: int) -> int:
    """Return the page to show after pressing `key`. Wraps around at both ends."""
    if key in {"n", "next"}:
        return (index + 1) % total
    if key in {"p", "prev", "previous"}:
        return (index - 1) % total
    return index


class UnoView:
    """
    Owns all terminal rendering and user input for a game of Uno.

    Game/round logic should never call cinput/cprint/sleep directly —
    it should ask this class to do it.
    """

    def __init__(self, context) -> None:
        self.context = context

    def display_topbar(self, margin=None) -> None:
        clear_screen()
        display_topbar(self.context.account, UNO_HEADER)

    # warning to look away when cards switch
    def player_switch_warning(self, current_player) -> None:
        self.display_topbar()
        cinput(f"Press enter to reveal {current_player.name}'s cards.")
        self.display_topbar()

    def print_hand(self, cards) -> None:
        """Print the cards side by side."""
        card_lines = [
            card.front.strip("\n").splitlines()
            for card in cards
        ]
        max_lines = max(len(lines) for lines in card_lines)

        # pad cards
        for lines in card_lines:
            while len(lines) < max_lines:
                lines.append(" " * len(lines[0]))

        # combine lines horizontally
        combined_lines = []
        for i in range(max_lines):
            combined_lines.append(
                "  ".join(card_lines[j][i] for j in range(len(cards)))
            )

        hand_string = "\n".join(combined_lines)
        cprint(hand_string)

    def prompt_num_players(self) -> int:
        return int(cinput("Input number of players (2-6):"))

    def prompt_player_name(self, i: int) -> str:
        return cinput("Player " + str(i + 1) + " Name: ")

    def show_turn(self, player, current_card) -> None:
        cprint("Player: " + player.name + "\n\nTop card of the Discard pile: \n" + str(current_card) + "\nYour hand:")
        self.print_hand(player.hand)
        cprint("\nCards from your hand that can be played:")
        if (bool(player.playable_cards(current_card))):
            self.print_hand(player.playable_cards(current_card))
        else:
            cprint("\nNONE\n")

    def prompt_draw_or_play(self) -> str:
        answer = cinput(DRAW_PROMPT).lower()
        while (answer != "d" and answer != "p" and answer != "draw" and answer != "play"):
            cprint("Please input either P or D!")
            answer = cinput(DRAW_PROMPT).lower()
        return answer

    def show_drawn_card(self, new_card) -> None:
        cprint("You drew \n" + str(new_card) + " from the pile.")

    def prompt_which_card(self) -> str:
        cprint(WHICH_CARD_PROMPT1)
        cprint(WHICH_CARD_PROMPT2)
        return cinput(WHICH_CARD_PROMPT3)

    def prompt_invalid_card(self) -> str:
        return cinput(INVALID_CARD_MSG).lower()

    def show_winner(self, winner, players) -> None:
        """Show the summary table, then let the user page through each player's stats."""
        self.display_topbar()
        cprint(f"{winner.name} is the winner!\n")
        cprint(format_summary_table(players))
        choice = cinput("Press [Enter] to view each player's stats or [q] to exit").lower()
        if choice in QUIT_KEYS:
            return
        self.show_player_pages(winner, players)

    def show_player_pages(self, winner, players) -> None:
        """Page through one stats screen per player using [n]ext / [p]revious / [q]uit."""
        index = 0
        while True:
            self.display_topbar()
            cprint(format_player_page(players[index], winner, index, len(players)))
            key = cinput("[n] next   [p] previous   [q] exit").lower()
            if key in QUIT_KEYS:
                return
            index = next_page_index(index, key, len(players))

    def prompt_wild_color(self) -> str:
        new_color = cinput("Choose a color for the wild card (green, yellow, red, or blue)!").lower()
        while (new_color != "green" and
               new_color != "red" and
               new_color != "yellow" and
               new_color != "blue"):
            new_color = cinput("Choose a valid color please (green, yellow, red, or blue).").lower()
        return new_color

    def prompt_wild_color_draw_4(self) -> str:
        new_color = cinput("Choose a color for the +4 card (green, yellow, red, or blue)!").lower()
        while (new_color != "green" and
               new_color != "red" and
               new_color != "yellow" and
               new_color != "blue"):
            new_color = cinput("Choose a valid color please (green, yellow, red, or blue).").lower()
        return new_color

    def prompt_next_player(self) -> None:
        cinput("Press enter when ready to switch to the next player")
