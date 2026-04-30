import os
from dotenv import load_dotenv

load_dotenv()

# Google credentials
GOOGLE_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "service-account.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# User profile — used by Claude to score relevance
USER_PROFILE = """
Software Engineer II with ~2 years experience at a Taiwan startup (foundi).
Background: EE degree (National Sun Yat-sen University), bootcamp (AppWorks School), full-stack with Angular/Node.js/React.
Strengths: Frontend (Angular, React, Chart.js), Elasticsearch, Redis pub/sub, real-time systems, frontend testing.
Weak areas: CS fundamentals — did not study CS undergrad, so missing formal foundations in OS, databases, networking, and concurrency.

Goal 1: Prepare for CMU 15-319 Cloud Computing (starting Summer 2026).
Key topics to cover:
- Virtualization, hypervisors, containers (Docker, Kubernetes)
- Auto-scaling, load balancing, cloud-native architecture
- AWS core services (EC2, S3, Lambda, DynamoDB, SQS, etc.)
- MapReduce, Spark, distributed data processing
- Cloud storage systems, CDNs, caching strategies
- Cost optimization, monitoring, cloud security basics

Goal 2: Prepare for Fall 2026 tech internship interviews (targeting FAANG/top tech companies).
Key topics to cover:
- System design — scalable architectures, trade-offs, real-world system breakdowns
- Distributed systems fundamentals — consistency, availability, partition tolerance
- API design, database schema design, caching strategies
- Concurrency, multithreading, and parallel programming concepts
- Note: DSA/leetcode is covered separately — no algorithm articles needed

Article selection guidance:
- Split roughly 60/40 between cloud computing prep and interview prep
- Prioritize cloud computing topics I'm weakest in: virtualization, MapReduce/Spark, cloud infrastructure
- For interview prep, favor system design deep-dives over algorithm content
- Mix of short blog posts (10-20 min, weekdays) and longer papers (weekends, 1-2x per week max)
- Prefer articles that build intuition and explain "why" over dry references
- Real-world engineering case studies (how Netflix/Google/Meta built X) are great for both goals
"""
