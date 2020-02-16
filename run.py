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

def get_tagged_repos():
    repos = []

    url = '/search/repositories?q=topic:' + HACKILLINOIS_TAG + '&page={}&per_page=100'
    page = 1
    while (True):
        result = get(url.format(page))
        page += 1
        if (len(result['items']) == 0):
            break
        for item in result['items']:
            repos.append(item['full_name'])
    return repos

def main():
    res = get('/users/benpankow/events/public')
    print(json.dumps(res, indent=2))
    
    '''repos = get_tagged_repos()

    since = (datetime.utcnow() - timedelta(hours = 12)).isoformat()

    total_commits = 0
    commits_url = '/repos/{}/commits?since=' + str(since)
    for repo in repos:
        print(commits_url.format(repo))
        result = get(commits_url.format(repo))
        total_commits += len(result)
        #print(json.dumps(result, indent=2))
    print(total_commits)'''

if __name__== '__main__':
	main()
