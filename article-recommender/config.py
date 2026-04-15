import os
from dotenv import load_dotenv

load_dotenv()

# Google credentials
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# User profile — used by Claude to score relevance
USER_PROFILE = """
Software Engineer II with ~2 years experience at a Taiwan startup (foundi).
Background: EE degree (National Sun Yat-sen University), bootcamp (AppWorks School), full-stack with Angular/Node.js/React.
Strengths: Frontend (Angular, React, Chart.js), Elasticsearch, Redis pub/sub, real-time systems, frontend testing.
Weak areas: CS fundamentals — did not study CS undergrad, so missing formal foundations in OS, databases, networking, and concurrency.

Goal: Senior Software Engineer at a top tech company (Google, Amazon, Meta).
Near-term: Starting CMU Master of Software Engineering (Summer 2026). Preparing for these courses:
1. 15-445/645 Database Systems — storage engines, B-trees, query optimization, transactions, concurrency control
2. 15-619 Cloud Computing — virtualization, containers, auto-scaling, cloud-native architecture
3. 15-440/640 Distributed Systems — RPC, consensus, replication, fault tolerance
4. 15-410 Operating System Design and Implementation — processes, threads, virtual memory, scheduling, syscalls
5. 15-618 Parallel Computer Architecture and Programming — concurrency, parallelism, memory models, GPU programming
6. 15-642 Machine Learning Systems — ML infrastructure, training pipelines, serving systems
7. 15-641 Networking and the Internet — TCP/IP, congestion control, DNS, HTTP, routing

Article selection guidance:
- Spread across ALL 7 course areas over time, not just distributed systems
- Prioritize areas I'm weakest in: OS, databases, networking, parallel computing (these are new to me)
- Distributed systems is already well-covered — only send if it fills a specific gap
- Mix of short blog posts (10-20 min, weekdays) and longer papers (weekends, 1-2x per week max)
- Prefer articles that build intuition and explain "why" over dry references
- Engineering leadership and design patterns are still welcome but secondary to course prep
"""
