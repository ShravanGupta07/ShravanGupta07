import os
import requests
from datetime import datetime, timezone

USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

BASE_URL = "https://api.github.com"


def get_repositories():
    repositories = []
    page = 1

    while True:
        url = f"{BASE_URL}/user/repos"
        params = {
            "per_page": 100,
            "page": page,
            "affiliation": "owner",
            "visibility": "all"
        }

        response = requests.get(
            url,
            headers=HEADERS,
            params=params
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


def get_year_stats(repositories, year):
    start = f"{year}-01-01T00:00:00Z"
    end = f"{year + 1}-01-01T00:00:00Z"

    total_commits = 0
    my_commits = 0
    contributors = set()

    for repo in repositories:

        # Ignore archived repositories
        if repo.get("archived"):
            continue

        owner = repo["owner"]["login"]
        name = repo["name"]

        page = 1

        while True:

            url = f"{BASE_URL}/repos/{owner}/{name}/commits"

            params = {
                "since": start,
                "until": end,
                "per_page": 100,
                "page": page
            }

            response = requests.get(
                url,
                headers=HEADERS,
                params=params
            )

            if response.status_code != 200:
                print(
                    f"Skipping {owner}/{name}: "
                    f"{response.status_code}"
                )
                break

            commits = response.json()

            if not commits:
                break

            for commit in commits:

                author = commit.get("author")

                if author and author.get("login"):
                    login = author["login"]

                    # Ignore bots
                    if not login.endswith("[bot]"):
                        contributors.add(login)

                        total_commits += 1

                        if login.lower() == USERNAME.lower():
                            my_commits += 1

            if len(commits) < 100:
                break

            page += 1

    return {
        "my_commits": my_commits,
        "total_commits": total_commits,
        "contributors": len(contributors)
    }


def replace_stats(readme, year, stats):

    start_marker = f"<!-- STATS_{year}_START -->"
    end_marker = f"<!-- STATS_{year}_END -->"

    content = f"""
{start_marker}

### 📅 {year}

| 📝 My Commits | 👥 Contributors | 🤝 Community Commits |
|---:|---:|---:|
| **{stats['my_commits']}** | **{stats['contributors']}** | **{stats['total_commits']}** |

{end_marker}
""".strip()

    start = readme.find(start_marker)
    end = readme.find(end_marker)

    if start != -1 and end != -1:

        end += len(end_marker)

        return (
            readme[:start]
            + content
            + readme[end:]
        )

    return readme + "\n\n" + content + "\n"


def main():

    repositories = get_repositories()

    current_year = datetime.now(timezone.utc).year

    years = [
        current_year,
        current_year - 1
    ]

    with open("README.md", "r", encoding="utf-8") as file:
        readme = file.read()

    for year in years:

        print(f"Calculating statistics for {year}...")

        stats = get_year_stats(
            repositories,
            year
        )

        print(stats)

        readme = replace_stats(
            readme,
            year,
            stats
        )

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(readme)


if __name__ == "__main__":
    main()
