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
Background: EE degree, bootcamp (AppWorks School), full-stack with Angular/Node.js/React.
Strengths: Frontend (Angular, React, Chart.js), Elasticsearch, Redis pub/sub, real-time systems, frontend testing.
Goal: Senior Software Engineer at FAANG (Google, Amazon, Meta).

Key areas to develop:
- System design at scale (distributed systems, sharding, replication, consensus, load balancing)
- Backend depth (database internals, caching strategies, message queues at scale)
- CS fundamentals (concurrency, networking, OS-level concepts)
- How things work under the hood (internals of databases, compilers, operating systems, networks, runtimes — deepens fundamental understanding)
- Algorithms (real-world applications, not just leetcode)
- Design patterns (Gang of Four, SOLID, real-world usage in large codebases)
- Engineering leadership (technical decision-making, RFC writing, cross-team influence)
- Observability & reliability (monitoring, SLOs, incident response, chaos engineering)
"""
