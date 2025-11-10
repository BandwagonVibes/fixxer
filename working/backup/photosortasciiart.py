import time
import os
import shutil
from colorama import init, Fore, Style

init(autoreset=True)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def center_text(text):
    width = shutil.get_terminal_size((80, 20)).columns
    return '\n'.join(line.center(width) for line in text.strip('\n').split('\n'))

def colored_square(char):
    return f"{Fore.RED}[▓]{Style.RESET_ALL}" if char == '▓' else f"{Fore.WHITE}[░]{Style.RESET_ALL}"

def photosort_animation(mode="startup"):
    header = f"""
{Fore.GREEN}{Style.BRIGHT}╔════════════════════════════════════════════════════════════╗
║  PHOTOSORT v1.0 - AI Ingestion Engine                      ║
║  cracked by ∞vision crew | serial: 1337-IMG-SORT-∞         ║
║  use responsibly. unleash creatively.                      ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

    frames = []

    if mode == "startup":
        frames = [
            [
                ['▓','░','▓','░'],
                ['░','▓','░','▓'],
                ['▓','░','▓','░'],
                "PHOTOSORT: AI Ingestion Engine"
            ],
            [
                ['▓','▓','░','░'],
                ['▓','▓','░','░'],
                ['▓','▓','░','░'],
                "Sorting images..."
            ],
            [
                ['▓','▓','░','░'],
                ['▓','▓','░','░'],
                ['▓','▓','░','░'],
                "PHOTOSORT — Chaos to Clarity"
            ]
        ]

    for frame in frames:
        clear_console()
        print(center_text(header))
        grid, caption = frame[:-1], frame[-1]
        for row in grid:
            print(center_text(' '.join(colored_square(c) for c in row)))
        print("\n" + center_text(f"{Fore.CYAN}{caption}{Style.RESET_ALL}"))
        time.sleep(1.5)

# Example usage:
if __name__ == "__main__":
    photosort_animation("startup")  