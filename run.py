import requests
import json
from datetime import datetime, timedelta

from secrets import *

GITHUB_API_BASE = 'https://api.github.com'

HACKILLINOIS_API_BASE = 'https://api.hackillinois.org'

TOKEN_IDX = 0

def get_gh_header():
    return {
        'Authorization': 'token ' + OAUTH_TOKENS[TOKEN_IDX],
        'Accept': 'application/vnd.github.v3+json'
    }

def get_gh(endpoint):
    url = GITHUB_API_BASE + endpoint
    resp = requests.get(url, headers=get_gh_header())

    remaining_reqs = int(resp.headers['x-ratelimit-remaining'])
    if remaining_reqs < 5:
        TOKEN_IDX = (TOKEN_IDX + 1) % len(OAUTH_TOKENS)
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

def main():
    usernames = get_user_list()

    total = 0
    for username in usernames:
        events = get_gh('/users/' + username + '/events')
        for event in events:
            et = event['type']
            if et == 'PushEvent':
                total += event['payload']['size']
            if False and et == 'PullRequestEvent' and event['payload']['action'] == 'opened':
                print(event['payload']['pull_request']['url'])
        print(total)
    print(total)
    write_blob({
        'foo': 'bar',
        'stuff': 123,
    })
    
if __name__== '__main__':
    main()
