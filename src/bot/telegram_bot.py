"""
Main Telegram bot module.
This file is now located in src/bot/ for better organization.
Entry point is in the root main.py file.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import main

if __name__ == '__main__':
    main()