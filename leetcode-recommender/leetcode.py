import time

import requests

GRAPHQL_URL = "https://leetcode.com/graphql/"
USER_AGENT = "LeetCodeRecommender/1.0"

CATALOG_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
    total: totalNum
    questions: data {
      acRate
      difficulty
      frontendQuestionId: questionFrontendId
      title
      titleSlug
      topicTags { name slug }
      isPaidOnly
    }
  }
}
"""



def fetch_problem_catalog() -> list[dict]:
    """Fetch all Medium/Hard free problems from LeetCode.

    Returns list of dicts with keys: id, title, slug, difficulty, tags, acceptance_rate
    """
    all_problems = []
    page_size = 100
    skip = 0

    # First request to get total count
    resp = _graphql_request(CATALOG_QUERY, {
        "categorySlug": "",
        "limit": page_size,
        "skip": 0,
        "filters": {},
    })
    data = resp["data"]["problemsetQuestionList"]
    total = data["total"]
    all_problems.extend(_parse_problems(data["questions"]))

    # Paginate through remaining
    skip = page_size
    while skip < total:
        time.sleep(1)  # Rate limiting
        resp = _graphql_request(CATALOG_QUERY, {
            "categorySlug": "",
            "limit": page_size,
            "skip": skip,
            "filters": {},
        })
        data = resp["data"]["problemsetQuestionList"]
        all_problems.extend(_parse_problems(data["questions"]))
        skip += page_size
        print(f"       Fetched {min(skip, total)}/{total} problems...")

    return all_problems


def fetch_solved_history(session_cookie: str) -> list[dict]:
    """Fetch all solved problems using the catalog query with status=AC filter.

    Returns list of dicts with keys: id, title, slug, solved_date
    """
    all_solved = []
    page_size = 100
    skip = 0

    # First request to get total count
    resp = _graphql_request_auth(CATALOG_QUERY, {
        "categorySlug": "",
        "limit": page_size,
        "skip": 0,
        "filters": {"status": "AC"},
    }, session_cookie)
    data = resp["data"]["problemsetQuestionList"]
    total = data["total"]
    all_solved.extend(_parse_solved(data["questions"]))

    # Paginate through remaining
    skip = page_size
    while skip < total:
        time.sleep(1)  # Rate limiting
        resp = _graphql_request_auth(CATALOG_QUERY, {
            "categorySlug": "",
            "limit": page_size,
            "skip": skip,
            "filters": {"status": "AC"},
        }, session_cookie)
        data = resp["data"]["problemsetQuestionList"]
        all_solved.extend(_parse_solved(data["questions"]))
        skip += page_size
        print(f"       Fetched {min(skip, total)}/{total} solved problems...")

    return all_solved


def get_problem_url(slug: str) -> str:
    """Return the LeetCode problem URL for a given slug."""
    return f"https://leetcode.com/problems/{slug}/"


def _graphql_request(query: str, variables: dict) -> dict:
    """Make a GraphQL request to LeetCode (no auth)."""
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _graphql_request_auth(query: str, variables: dict, session_cookie: str) -> dict:
    """Make an authenticated GraphQL request to LeetCode."""
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={
            "User-Agent": USER_AGENT,
            "Cookie": f"LEETCODE_SESSION={session_cookie}",
            "Referer": "https://leetcode.com",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_solved(questions: list[dict]) -> list[dict]:
    """Parse solved question data into our format."""
    solved = []
    for q in questions:
        solved.append({
            "id": str(q.get("frontendQuestionId", "")),
            "title": q.get("title", ""),
            "slug": q.get("titleSlug", ""),
            "solved_date": "",
        })
    return solved


def _parse_problems(questions: list[dict]) -> list[dict]:
    """Parse raw GraphQL question data into our format. Filters to Medium/Hard, free only."""
    problems = []
    for q in questions:
        if q.get("isPaidOnly"):
            continue
        difficulty = q.get("difficulty", "")
        if difficulty == "Easy":
            continue
        tags = [t["name"] for t in q.get("topicTags", [])]
        problems.append({
            "id": str(q.get("frontendQuestionId", "")),
            "title": q.get("title", ""),
            "slug": q.get("titleSlug", ""),
            "difficulty": difficulty,
            "tags": tags,
            "acceptance_rate": round(q.get("acRate", 0), 1),
        })
    return problems
