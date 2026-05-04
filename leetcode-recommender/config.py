import os

from dotenv import load_dotenv

load_dotenv()

# Google credentials
GOOGLE_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "service-account.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LEETCODE_SESSION = os.getenv("LEETCODE_SESSION", "")

# User profile — used by Claude to select problems
USER_PROFILE = """
Software Engineer II with ~2 years experience at a Taiwan startup (foundi).
Background: EE degree (National Sun Yat-sen University), bootcamp (AppWorks School), full-stack with Angular/Node.js/React.
700+ LeetCode problems already solved.

Goal: Prepare for Fall 2026 tech internship interviews at Mag 7 / FAANG companies.

Focus areas for LeetCode practice:
- Dynamic Programming (state transitions, optimization, interval DP, bitmask DP)
- Graphs (BFS/DFS, shortest path, topological sort, union-find)
- Trees (binary trees, BST, segment trees, tries)
- Sliding Window / Two Pointers
- Stack / Monotonic Stack
- Binary Search (on answer, rotated arrays)
- Greedy algorithms
- Backtracking
- Heap / Priority Queue
- Bit Manipulation

Selection guidance:
- Only Medium and Hard problems (Easy is not interview-relevant at this level)
- Prioritize topics I'm weakest in based on my feedback history
- Provide topic diversity — 3 different topics per batch when possible
- Favor problems that test patterns commonly seen in Mag 7 interviews
"""
