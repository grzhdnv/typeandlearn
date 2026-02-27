# Mostly gemini proof of concept and minimum viable product

import curses
import random
import sys
import argparse
import os

DEFAULT_WORDS = ["python", "terminal", "typing", "practice", "minimalist", "focus", "flow"]

class TypingTest:
    def __init__(self, target_text):
        self.target_text = target_text
        self.typed_text = ""
        
    def get_accuracy(self):
        if not self.typed_text:
            return 100.0
        correct = sum(1 for i, c in enumerate(self.typed_text) 
                     if i < len(self.target_text) and c == self.target_text[i])
        return round((correct / len(self.typed_text)) * 100, 1)

def load_words(file_path, count):
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                words = [w.strip() for w in f.read().split() if w.strip()]
        else:
            words = DEFAULT_WORDS
        random.shuffle(words)
        return " ".join(words[:count])
    except Exception:
        return "Error loading file."

def run_test(stdscr, args):
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1) 
    curses.init_pair(2, curses.COLOR_RED, -1)   
    curses.init_pair(3, 244, -1)                
    curses.curs_set(0) 

    target_text = load_words(args.file, args.n)
    test = TypingTest(target_text)

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        
        acc = test.get_accuracy()
        label = f" ACC: {acc}% | PROGRESS: {len(test.typed_text)}/{len(target_text)} "
        stdscr.addstr(1, 2, label, curses.A_REVERSE)

        y, x = 3, 2
        for i, char in enumerate(target_text):
            attr = curses.color_pair(3)
            if i < len(test.typed_text):
                attr = curses.color_pair(1) if test.typed_text[i] == char else curses.color_pair(2)
            
            if i == len(test.typed_text):
                attr |= curses.A_STANDOUT

            if x >= width - 4:
                y += 1
                x = 2
            
            try:
                stdscr.addch(y, x, char, attr)
            except curses.error:
                pass 
            x += 1

        stdscr.refresh()

        if len(test.typed_text) == len(target_text):
            # Return the stats to be printed after curses closes
            return acc, len(test.typed_text), target_text.count(' ') + 1

        key = stdscr.getch()
        if key == 27: return None # Exit without stats if ESC is pressed
        if key == 3: sys.exit() 
        
        if key in (curses.KEY_BACKSPACE, 127, 8):
            test.typed_text = test.typed_text[:-1]
        elif 32 <= key <= 126:
            test.typed_text += chr(key)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file")
    parser.add_argument("-n", type=int, default=25)
    args = parser.parse_args()

    # Capture the return value from the wrapper
    results = curses.wrapper(run_test, args)

    # Print to the regular terminal after the TUI disappears
    if results:
        accuracy, chars, words = results
        print("\n" + "—" * 30)
        print(" COMPLETE ")
        print("—" * 30)
        print(f" Accuracy:   {accuracy}%")
        print(f" Characters: {chars}")
        print(f" Words:      {words}")
        print("—" * 30 + "\n")
    else:
        print("\nAborted.\n")

if __name__ == "__main__":
    main()
