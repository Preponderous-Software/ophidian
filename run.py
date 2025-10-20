import sys
import os
import argparse

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ophidian import Ophidian

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ophidian - A snake game')
    parser.add_argument('--text-ui', action='store_true',
                        help='Use text-based UI instead of graphical UI')
    args = parser.parse_args()
    
    ophidian = Ophidian(use_text_ui=args.text_ui)
    ophidian.run()
