import requests
import json
from datetime import datetime, timedelta
import time
import pytz
import sys

from secrets import *

GITHUB_API_BASE = "https://api.github.com"

HACKILLINOIS_API_BASE = "https://api.hackillinois.org"

MAX_PR_ENTRIES = 25

token_idx = 0


def get_gh_header():
    return {
        "Authorization": "token " + OAUTH_TOKENS[token_idx],
        "Accept": "application/vnd.github.v3+json",
    }


def get_gh(endpoint):
    global token_idx

    url = GITHUB_API_BASE + endpoint
    resp = requests.get(url, headers=get_gh_header())

    remaining_reqs = int(resp.headers["x-ratelimit-remaining"])
    if remaining_reqs % 1000 == 0:
        print(f"{remaining_reqs} left")
    if remaining_reqs < 5:
        token_idx = (token_idx + 1) % len(OAUTH_TOKENS)
    return resp.json()


def get_hi_header():
    return {"Authorization": HI_JWT, "Content-Type": "application/json"}


def get_hi(endpoint):
    url = HACKILLINOIS_API_BASE + endpoint
    resp = requests.get(url, headers=get_hi_header())
    return resp.json()


def put_hi(endpoint, data):
    url = HACKILLINOIS_API_BASE + endpoint
    resp = requests.put(url, data=json.dumps(data), headers=get_hi_header())
    return resp.json()


def get_blob(name):
    """Gets the JSON object associated with the given blobstore entry."""

    return get_hi(f"/upload/blobstore/{name}/")["data"]


def write_blob(name, blob):
    """Writes an arbitrary Python dict to the given blobstore entry."""

    blob = {"id": name, "data": blob}
    return put_hi("/upload/blobstore/", blob)


def get_user_list():
    """Gets all checked-in users and returns their GitHub usernames."""

    res = get_hi("/checkin/list/")
    checkin_user_ids = set(res["checkedInUsers"])

    res = get_hi("/rsvp/filter/")
    rsvp_user_ids = set([user["id"] for user in res["rsvps"] if user["isAttending"]])

    user_ids = checkin_user_ids | rsvp_user_ids

    ids_query = ",".join(user_ids)
    res = get_hi(f"/registration/attendee/filter/?id={ids_query}")
    attendee_github_usernames = [user["github"] for user in res["registrations"]]

    res = get_hi(f"/registration/mentor/filter/")
    mentor_github_usernames = [user["github"] for user in res["registrations"]]

    github_usernames = list(set(mentor_github_usernames + attendee_github_usernames))

    return github_usernames


def main():
    blob = {"history": [], "pr_feed": [], "last_updated": 0}

    total_commits = 0
    total_prs = 0
    total_opened_issues = 0
    total_closed_issues = 0
    total_loc = 0
    pr_feed = []
    pr_languages = {}

    # keep track of seen events so we don't re-process things we've seen already
    seen_ids = set()
    seen_commits = set()

    config = get_blob("git-stats-config")

    max_hist_entries = config["maxHistEntries"]
    time_interval = timedelta(seconds=config["intervalSecs"])
    cutoff_time = datetime.fromtimestamp(config["cutoffTime"], pytz.utc)

    last_update_time = cutoff_time

    # see if stats has run previously, if so get most recent data
    last_update = get_blob("git-stats")
    if "history" in last_update and len(last_update["history"]) > 0:
        blob = last_update

        last_update_numbers = last_update["history"][0]
        total_commits = last_update_numbers["totalCommits"]
        total_prs = last_update_numbers["totalPRs"]
        total_opened_issues = last_update_numbers["totalOpenedIssues"]
        total_closed_issues = last_update_numbers["totalClosedIssues"]
        pr_languages = last_update_numbers["prLanguages"]
        pr_feed = last_update["prFeed"]
        total_loc = last_update_numbers["totalLoc"]

        last_update_time = datetime.fromtimestamp(last_update_numbers["time"], pytz.utc)

    # only look at events newer than both the cutoff time and the last update
    if last_update_time > cutoff_time:
        cutoff_time = last_update_time
    while True:
        # run update every specified interval
        # the runtime of run_update is included this window
        next_update_time = datetime.now(pytz.utc) + time_interval

        commits = []

        # run one update
        usernames = get_user_list()
        for username in usernames:
            events = get_gh("/users/" + username + "/events")

            try:
                for event in events:
                    # ignore seen events or events before time cutoff
                    event_time = event["created_at"]
                    event_time = event_time.replace(
                        "Z", "+00:00"
                    )  # hack to get fromisoformat to work
                    event_time = datetime.fromisoformat(event_time)

                    if event_time < cutoff_time:
                        break
                    if event["id"] in seen_ids:
                        break
                    seen_ids.add(event["id"])

                    et = event["type"]
                    if et == "IssuesEvent":
                        if event["payload"]["action"] == "opened":
                            total_opened_issues += 1
                        if event["payload"]["action"] == "closed":
                            total_closed_issues += 1
                    if et == "PushEvent":
                        total_commits += event["payload"]["size"]
                        for commit in event["payload"]["commits"]:
                            sha = commit["sha"]
                            if sha in seen_commits:
                                continue
                            seen_commits.add(sha)
                            commits.append(commit["url"])
                    if (
                        et == "PullRequestEvent"
                        and event["payload"]["action"] == "opened"
                    ):
                        total_prs += 1
                        pr_language = event["payload"]["pull_request"]["head"]["repo"][
                            "language"
                        ]
                        if pr_language not in pr_languages:
                            pr_languages[pr_language] = 1
                        else:
                            pr_languages[pr_language] += 1
                        pr_feed = [
                            {
                                "name": event["actor"]["display_login"],
                                "avatarUrl": event["actor"]["avatar_url"],
                                "title": event["payload"]["pull_request"]["title"],
                                "repo": event["repo"]["name"],
                                "time": round(event_time.timestamp()),
                            }
                        ] + pr_feed[: MAX_PR_ENTRIES - 1]
            except TypeError as e:
                print(f"Error processing user {username}: {e}")

        for commit in commits:
            try:
                info = get_gh(commit[22:])
                if "stats" in info:
                    total_loc += info["stats"]["total"]
            except TypeError as e:
                print(f"Error processing commit: {e}")

        last_update_time = round(datetime.now(pytz.utc).timestamp())

        print(f"Completed update at {last_update_time}")
        sys.stdout.flush()

        blob["lastUpdated"] = last_update_time
        blob["prFeed"] = pr_feed
        # add new history entry, store up to MAX_ENTRIES of these
        blob["history"] = [
            {
                "totalCommits": total_commits,
                "totalPRs": total_prs,
                "totalOpenedIssues": total_opened_issues,
                "totalClosedIssues": total_closed_issues,
                "prLanguages": pr_languages,
                "totalLoc": total_loc,
                "time": last_update_time,
            }
        ] + blob["history"][: max_hist_entries - 1]

        write_blob("git-stats", blob)

        cur_time = datetime.now(pytz.utc)
        to_wait = next_update_time - cur_time
        if to_wait.total_seconds() > 0:
            time.sleep(to_wait.total_seconds())


if __name__ == "__main__":
    main()
