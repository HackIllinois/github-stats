import requests
import json
from datetime import datetime, timedelta
import time
import pytz

from secrets import *

GITHUB_API_BASE = 'https://api.github.com'

HACKILLINOIS_API_BASE = 'https://api.hackillinois.org'

TIME_INTERVAL =  timedelta(seconds=30)

CUTOFF_TIME = datetime(2020, 2, 19, tzinfo=pytz.timezone('America/Chicago'))

MAX_HIST_ENTRIES = 25
MAX_PR_ENTRIES = 25

token_idx = 0
def get_gh_header():
    return {
        'Authorization': 'token ' + OAUTH_TOKENS[token_idx],
        'Accept': 'application/vnd.github.v3+json'
    }

def get_gh(endpoint):
    global token_idx
    
    url = GITHUB_API_BASE + endpoint
    resp = requests.get(url, headers=get_gh_header())

    remaining_reqs = int(resp.headers['x-ratelimit-remaining'])
    if remaining_reqs < 5:
        token_idx = (token_idx + 1) % len(OAUTH_TOKENS)
    return resp.json()

def get_hi_header():
    return {
        'Authorization': HI_JWT,
        'Content-Type': 'application/json'
    }

def get_hi(endpoint):
    url = HACKILLINOIS_API_BASE + endpoint
    resp = requests.get(url, headers=get_hi_header())
    return resp.json()

def put_hi(endpoint, data):
    url = HACKILLINOIS_API_BASE + endpoint
    resp = requests.put(url, data=json.dumps(data), headers=get_hi_header())
    return resp.json()

def write_blob(blob):
    """Writes an arbitrary Python dict to the 'git-stats' blobstore entry."""

    blob = {
        'id': 'git-stats',
        'data': blob,
    }
    return put_hi('/upload/blobstore/', blob)

def get_user_list():
    """Gets all checked-in users and returns their GitHub usernames."""

    res = get_hi('/checkin/list/')
    checkin_user_ids = set(res['checkedInUsers'])

    res = get_hi('/rsvp/filter/')
    rsvp_user_ids = set([user['id'] for user in res['rsvps'] if user['isAttending']])

    user_ids = checkin_user_ids | rsvp_user_ids    

    ids_query = ','.join(user_ids)
    res = get_hi(f'/registration/attendee/filter/?id={ids_query}')
    github_usernames = [user['github'] for user in res['registrations']]

    return github_usernames


def main():
    blob = {
        'history': [],
        'pr_feed': [],
        'last_updated': 0,
    }

    total_commits = 0
    total_prs = 0
    total_opened_issues = 0
    total_closed_issues = 0
    pr_feed = []
    pr_languages = {}

    # keep track of seen events so we don't re-process things we've seen already
    seen_ids = set()

    while True:
        # run update every specified interval
        # the runtime of run_update is included this window
        next_update_time = datetime.now() + TIME_INTERVAL

        # run one update
        usernames = get_user_list()
        for username in usernames:
            events = get_gh('/users/' + username + '/events')

            try:
              for event in events:
                # ignore seen events or events before time cutoff
                    event_time = event['created_at']
                    event_time = event_time.replace('Z', '+00:00') # hack to get fromisoformat to work
                    event_time = datetime.fromisoformat(event_time)
                    if event_time <= CUTOFF_TIME:
                        break
                    if event['id'] in seen_ids:
                        break
                    seen_ids.add(event['id'])
                    
                    et = event['type']
                    if et == 'IssuesEvent':
                        if event['payload']['action'] == 'opened':
                            total_opened_issues += 1 
                        if event['payload']['action'] == 'closed':
                            total_closed_issues += 1 
                    if et == 'PushEvent':
                        total_commits += event['payload']['size']
                    if et == 'PullRequestEvent' and event['payload']['action'] == 'opened':
                        total_prs += 1
                        pr_language = event['payload']['pull_request']['head']['repo']['language']
                        if pr_language not in pr_languages:
                            pr_languages[pr_language] = 1
                        else:
                            pr_languages[pr_language] += 1
                        pr_feed = [{
                            'name': event['actor']['display_login'],
                            'avatar_url': event['actor']['avatar_url'],
                            'title': event['payload']['pull_request']['title'],
                            'repo': event['repo']['name']
                        }] + pr_feed[:MAX_PR_ENTRIES - 1]
            except TypeError as e:
                print(f'Error processing user {username}: {e}')

        last_update_time = time.mktime(datetime.now().timetuple())
        print(f'Completed update at {last_update_time}')

        blob['last_updated'] = last_update_time
        blob['pr_feed'] = pr_feed
        # add new history entry, store up to MAX_ENTRIES of these
        blob['history'] = [{
            'total_commits': total_commits,
            'total_prs': total_prs,
            'total_opened_issues': total_opened_issues,
            'total_closed_issues': total_closed_issues,
            'pr_languages': pr_languages,
            'time': last_update_time
        }] + blob['history'][:MAX_HIST_ENTRIES - 1]

        write_blob(blob)

        cur_time = datetime.now()
        to_wait = next_update_time - cur_time
        if to_wait.total_seconds() > 0:
            time.sleep(to_wait.total_seconds())

    
if __name__== '__main__':
    main()
