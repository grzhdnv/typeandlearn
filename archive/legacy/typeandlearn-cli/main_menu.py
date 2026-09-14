import curses
import locale

# Handle Unicode for foreign characters
locale.setlocale(locale.LC_ALL, "")


def process(file_path):
    """
    Placeholder for your processing logic.
    Returns a list of sentences.
    """
    # Example output:
    return [
        "The cat sat on the warm windowsill and watched the birds outside.",
        "She decided to learn a new language before her trip abroad.",
        "The old library smelled of dust and forgotten stories.",
    ]


def run_sentence_session(stdscr, target_text, current_num, total_num):
    user_input = ""

    while True:
        stdscr.clear()

        # Header Info
        stdscr.addstr(1, 2, f"Sentence {current_num} of {total_num}", curses.A_REVERSE)

        # Line 3: The Reference (Static)
        stdscr.addstr(3, 2, "Target: ", curses.A_BOLD)
        stdscr.addstr(3, 10, target_text)

        # Line 5: The Interactive "Trace" Field
        stdscr.addstr(5, 2, "Type:   ", curses.A_BOLD)

        # 1. Render the 'Ghost' text (Opaque trailing)
        stdscr.addstr(5, 10, target_text, curses.A_DIM)

        # 2. Overlay the user's progress
        for i, char in enumerate(user_input):
            if i < len(target_text):
                # Check if character matches the target
                color = (
                    curses.color_pair(1)
                    if char == target_text[i]
                    else curses.color_pair(2)
                )
                stdscr.addstr(5, 10 + i, target_text[i], color)

        # Move cursor to the current typing position
        stdscr.move(5, 10 + len(user_input))
        stdscr.refresh()

        # Check for completion of the current sentence
        if len(user_input) == len(target_text):
            mistakes = sum(
                1 for i, char in enumerate(user_input) if char != target_text[i]
            )
            result_color = (
                curses.color_pair(1) if mistakes == 0 else curses.color_pair(2)
            )
            stdscr.addstr(
                7,
                2,
                f"Done! Mistakes: {mistakes}. Press any key for the next sentence...",
                result_color,
            )
            stdscr.getch()
            return True

        # Input Handling
        try:
            key = stdscr.get_wch()
        except Exception:
            continue

        if isinstance(key, str):
            if ord(key) == 127:  # Backspace
                user_input = user_input[:-1]
            elif ord(key) == 27:  # ESC to quit session
                return False
            else:
                # Prevent typing beyond the length of the sentence
                if len(user_input) < len(target_text):
                    user_input += key
        elif key == curses.KEY_BACKSPACE:
            user_input = user_input[:-1]


def main(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # Correct
    curses.init_pair(2, curses.COLOR_RED, -1)  # Error

    # 1. File Selection / Processing
    curses.echo()
    stdscr.addstr(1, 2, "TYPE AND LEARN", curses.A_BOLD)
    stdscr.addstr(3, 2, "Enter file path or drag-and-drop:")
    stdscr.addstr(4, 2, "> ")
    path = stdscr.getstr(4, 4).decode("utf-8").strip().strip("'\"")
    curses.noecho()

    # 2. Get the sentence list from your process function
    training_data = process(path)
    total = len(training_data)

    # 3. Loop through the sentence list
    for index, sentence in enumerate(training_data, 1):
        # Run the typing logic for each sentence
        continue_session = run_sentence_session(stdscr, sentence, index, total)

        if not continue_session:
            break

    stdscr.clear()
    stdscr.addstr(
        2, 2, "Session Complete! You've finished all sentences.", curses.A_BOLD
    )
    stdscr.addstr(3, 2, "Press any key to exit.")
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
