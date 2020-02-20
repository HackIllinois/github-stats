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
    blob = {
        'id': 'git-stats',
        'data': blob,
    }
    return put_hi('/upload/blobstore/', blob)

def get_user_list():
    res = get_hi('/rsvp/filter/')
    github_usernames = [user['registrationData']['attendee']['github'] for user in res['rsvps'] if user['isAttending']]
    return github_usernames

# keep track of seen events so we don't re-process things we've seen already
seen_ids = set()

total_commits = 0
total_prs = 0

def main():
    while True:
        ttime = datetime.now()
        next_update_time = ttime + TIME_INTERVAL
        
        run_update()

        ttime = datetime.now()
        to_wait = next_update_time - ttime
        print(to_wait)
        print(to_wait.total_seconds())
        if to_wait.total_seconds() > 0:
            time.sleep(to_wait.total_seconds())

    
def run_update():
    global total_commits, total_prs
    
    usernames = get_user_list()

    for username in usernames:
        events = get_gh('/users/' + username + '/events')
        for event in events:

            # ignore seen events or events before time cutoff
            event_time = event['created_at']
            event_time = event_time.replace('Z', '+00:00')
            event_time = datetime.fromisoformat(event_time)
            if event_time < CUTOFF_TIME:
                break
            if event['id'] in seen_ids:
                break
            seen_ids.add(event['id'])
            
            et = event['type']
            if et == 'PushEvent':
                total_commits += event['payload']['size']
            if et == 'PullRequestEvent' and event['payload']['action'] == 'opened':
                total_prs += 1
                pr_language = print(event['payload']['pull_request']['head']['repo']['language'])
    print(f'{total_commits} commits')
    write_blob({
        'total_commits': total_commits,
        'total_prs': total_prs,
        'last_update': time.mktime(datetime.now().timetuple())
    })
    
if __name__== '__main__':
    main()
