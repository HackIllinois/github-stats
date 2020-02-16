from urllib import request, parse
import json
from datetime import datetime, timedelta

from secrets import *

GITHUB_API_BASE = 'https://api.github.com'
HACKILLINOIS_TAG = 'hackillinois'

TOKEN_IDX = 0

def get_header():
    return {
        'Authorization': 'token ' + OAUTH_TOKENS[TOKEN_IDX],
        'Accept': 'application/vnd.github.mercy-preview+json'
    }

def get(endpoint):
    url = GITHUB_API_BASE + endpoint
    req = request.Request(url, headers=get_header())
    with request.urlopen(req) as response:
        remaining_reqs = int(response.getheader('X-RateLimit-Remaining'))
        if remaining_reqs < 5:
            TOKEN_IDX = (TOKEN_IDX + 1) % len(OAUTH_TOKENS)
            
        data = response.read()
    return json.loads(data)

def main():
    res = get('/users/benpankow/events/public')
    print(json.dumps(res, indent=2))

if __name__== '__main__':
	main()
