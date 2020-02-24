# github-stats
Live GitHub statistics for the HackIllinois event. Pulls information about GitHub PRs, issues, and commits and pushes them to the HackIllinois API.


Data format is as follows:
```
{
    "id": "git-stats",
    "data": {
        "history": [
            {
                "pr_languages": {
                    "Go": 1,
                    "Kotlin": 1,
                    "Swift": 1
                },
                "time": 1582579227,
                "total_closed_issues": 0,
                "total_commits": 494,
                "total_opened_issues": 1,
                "total_prs": 5
            }
        ],
        "last_updated": 1582579227,
        "pr_feed": [
            {
                "avatar_url": "https://avatars.githubusercontent.com/u/42848321?",
                "name": "PatrickKan",
                "repo": "HackIllinois/iOS",
                "title": "Fixes announcements with bell icon "
            },
            {
                "avatar_url": "https://avatars.githubusercontent.com/u/5103015?",
                "name": "patrickfeltes",
                "repo": "HackIllinois/android",
                "title": "Master"
            },
            {
                "avatar_url": "https://avatars.githubusercontent.com/u/10215173?",
                "name": "benpankow",
                "repo": "HackIllinois/api",
                "title": "Fix checkin override failing on no RSVP"
            }
        ]
    }
}
```
