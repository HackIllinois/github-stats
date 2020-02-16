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

def main():
    res = get_gh('/users/benpankow/events/public')
    # print(json.dumps(res, indent=2))

    res = get_hi('/user/filter/')
    print(json.dumps(res, indent=2))

if __name__== '__main__':
	main()
