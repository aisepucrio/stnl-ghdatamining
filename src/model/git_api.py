from datetime import datetime
import requests
from requests.models import _Params
from tqdm.auto import tqdm
from urllib.parse import urlparse

#TODO: Create documentation for complex functions
#TODO: Remove unnecessary try-except blocks
#TODO: Modularize the long methods (code smell)
#TODO: Implement a factory method for commit/issue/pull_request/branch
#TODO: Centralize the error handling
#TODO: Centralize the response obtaining, with the prupose of removing unnecessary error handling repetition

class Git_API:
    def __init__(self, token):
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.stop_process = False

    def get_repo_name(self, repo_url: str) -> str:
        path = urlparse(repo_url).path
        repo_name = path.lstrip('/')
        return repo_name
    
    #probably not a good place for this method
    def _extract_last_page_url(self, links):
        for link in links:
            if 'rel="last"' in link:
                return int(link[link.find('<') + 1:link.find('>')])

    def get_total_pages(self, url: str, params: _Params | None = None) -> int:
        response = requests.get(f"{url}?per_page=1",
                                headers=self.headers,
                                params=params)

        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            return self._extract_last_page_url(links)
        return 1

    def get_all_pages(self, url: str,
                      params: _Params | None = None,
                      date_key: datetime | None = None,
                      start_date: datetime | str | None = None,
                      end_date: datetime | str | None = None
                      ) -> list[dict[str, str]]:
        results = []

        # Ensure start_date and end_date are datetime.date objects
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        total_pages = self.get_total_pages(url, self.headers, params)

        with tqdm(total=total_pages, desc="pages", unit="page") as pbar:
            for page in range(1, total_pages + 1):
                if self.stop_process:
                    print("Process stopped by the user.")
                    break
                try:
                    if params:
                        params['page'] = page
                        response = requests.get(
                            url, headers=self.headers, params=params)
                    else:
                        response = requests.get(
                            f"{url}?page={page}&per_page=35", headers=self.headers)
                    response.raise_for_status()
                    data = response.json()

                    if date_key and start_date and end_date:
                        filtered_data = []
                        for item in data:
                            if 'commit' in item:
                                item_date = datetime.strptime(
                                    item['commit']['author']['date'],
                                    '%Y-%m-%dT%H:%M:%SZ'
                                    ).date()
                            else:
                                item_date = datetime.strptime(
                                    item[date_key],
                                    '%Y-%m-%dT%H:%M:%SZ').date()
                            if start_date <= item_date <= end_date:
                                filtered_data.append(item)
                            elif item_date < start_date:
                                break
                        results.extend(filtered_data)
                    else:
                        results.extend(data)

                    pbar.update(1)
                except requests.exceptions.RequestException as e:
                    print(
                        f'Error fetching data from URL: {url} with status {e.response.status_code}')
                    break
                except Exception as e:
                    print(
                        f'Unexpected error fetching data from URL: {url} - {str(e)}')
                    break

        if not results:
            print(f'No data found for {desc} in the given date range.')

        return results

    def get_comments_with_initial(
            self,
            issue_url,
            headers,
            initial_comment,
            issue_number,
            start_date,
            end_date):
        params = {
            'since': start_date,
            'until': end_date
        }
        comments = self.get_all_pages(
            issue_url,
            headers,
            f'Fetching comments for issue/pr #{issue_number}',
            params,
            'created_at',
            start_date,
            end_date)
        essential_comments = [{
            'user': initial_comment['user']['login'],
            'body': initial_comment['body'],
            'created_at': initial_comment['created_at']
        }]
        essential_comments.extend([{
            'user': comment['user']['login'],
            'body': comment['body'],
            'created_at': comment['created_at']
        } for comment in comments if 'user' in comment
          and 'login' in comment['user']
          and 'body' in comment
          and 'created_at' in comment])
        return essential_comments


def get_commits(self, repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/commits'
    params = {
        'since': start_date,
        'until': end_date,
        'per_page': 35
    }
    commits = self.get_all_pages(
        url,
        headers,
        'Fetching commits',
        params,
        'commit',
        start_date,
        end_date)
    essential_commits = [{
        'sha': commit['sha'],
        'message': commit['commit']['message'],
        'date': commit['commit']['author']['date'],
        'author': commit['commit']['author']['name']
    } for commit in commits if 'sha' in commit and 'commit' in commit and 'message' in commit['commit'] and 'author' in commit['commit'] and 'date' in commit['commit']['author'] and 'name' in commit['commit']['author']]
    return essential_commits


def get_issues(self, repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/issues'
    params = {
        'since': start_date,
        'until': end_date,
        'per_page': 35
    }
    issues = self.get_all_pages(
        url,
        headers,
        'Fetching issues',
        params,
        'created_at',
        start_date,
        end_date)
    essential_issues = []
    for issue in issues:
        if 'number' in issue and 'title' in issue and 'state' in issue and 'user' in issue and 'login' in issue[
                'user']:
            issue_comments_url = issue['comments_url']
            initial_comment = {
                'user': issue['user'],
                'body': issue['body'],
                'created_at': issue['created_at']
            }
            comments = self.get_comments_with_initial(
                issue_comments_url,
                headers,
                initial_comment,
                issue['number'],
                start_date,
                end_date)
            essential_issues.append({
                'number': issue['number'],
                'title': issue['title'],
                'state': issue['state'],
                'creator': issue['user']['login'],
                'comments': comments
            })
    return essential_issues


def get_pull_requests(self, repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/pulls'
    params = {
        'since': start_date,
        'until': end_date,
        'per_page': 35
    }
    pull_requests = self.get_all_pages(
        url,
        headers,
        'Fetching pull requests',
        params,
        'created_at',
        start_date,
        end_date)
    essential_pull_requests = []
    for pr in pull_requests:
        if 'number' in pr and 'title' in pr and 'state' in pr and 'user' in pr and 'login' in pr[
                'user']:
            pr_comments_url = pr['_links']['comments']['href']
            initial_comment = {
                'user': pr['user'],
                'body': pr['body'],
                'created_at': pr['created_at']
            }
            comments = self.get_comments_with_initial(
                pr_comments_url, headers, initial_comment, pr['number'], start_date, end_date)
            essential_pull_requests.append({
                'number': pr['number'],
                'title': pr['title'],
                'state': pr['state'],
                'creator': pr['user']['login'],
                'comments': comments
            })
    return essential_pull_requests


def get_branches(self, repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/branches'
    branches = self.get_all_pages(url, headers, 'Fetching branches')
    essential_branches = [{
        'name': branch['name'],
        'sha': branch['commit']['sha']
    } for branch in branches if 'name' in branch and 'commit' in branch and 'sha' in branch['commit']]
    return essential_branches