import requests
import json
import os
from dotenv import load_dotenv
from tqdm.auto import tqdm
from urllib.parse import urlparse

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')

# Define authentication headers
headers = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Control variable to stop the process
stop_process = False

# Function to get repository name
def get_repo_name(repo_url):
    try:
        path = urlparse(repo_url).path
        repo_name = path.lstrip('/')
        if len(repo_name.split('/')) != 2:
            raise ValueError("Invalid repository URL. Make sure it is in the format 'https://github.com/owner/repo'.")
        return repo_name
    except Exception as e:
        raise ValueError("Error parsing repository URL. Check the format and try again.")

# Function to get total number of pages
def get_total_pages(url, headers):
    try:
        response = requests.get(f"{url}?per_page=1", headers=headers)
        response.raise_for_status()
        
        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            for link in links:
                if 'rel="last"' in link:
                    last_page_url = link[link.find('<') + 1:link.find('>')]
                    return int(last_page_url.split('=')[-1])
        return 1
    except requests.exceptions.RequestException as e:
        if e.response.status_code == 404:
            raise ValueError("Repository not found.")
        elif e.response.status_code == 401:
            raise ValueError("Invalid or expired token.")
        elif e.response.status_code == 403:
            raise ValueError("Request limit reached.")
        else:
            raise Exception(f'Error fetching data from URL: {url} with status {e.response.status_code}')
    except Exception as e:
        raise Exception(f'Unexpected error: {str(e)}')

# Function to get all pages with specified number of pages
def get_all_pages_with_limit(url, headers, desc, max_pages):
    global stop_process
    results = []
    try:
        total_pages = get_total_pages(url, headers)
    except Exception as e:
        print(e)
        return results

    # Adjust max_pages if it exceeds total_pages
    if max_pages > total_pages:
        max_pages = total_pages

    with tqdm(total=max_pages, desc=desc, unit="page") as pbar:
        for page in range(1, max_pages + 1):
            if stop_process:
                print("Process stopped by the user.")
                break
            try:
                response = requests.get(f"{url}?page={page}&per_page=35", headers=headers)
                response.raise_for_status()
                data = response.json()
                results.extend(data)
                print(f'\nPage {page}: {len(data)} commits')
                pbar.update(1)
            except requests.exceptions.RequestException as e:
                print(f'Error fetching data from URL: {url} with status {e.response.status_code}')
                break
            except Exception as e:
                print(f'Unexpected error fetching data from URL: {url} - {str(e)}')
                break
    return results

# Example function to use the new pagination limit
def get_commits_with_page_limit(repo_url, max_pages):
    try:
        repo_name = get_repo_name(repo_url)
        url = f'https://api.github.com/repos/{repo_name}/commits'
        commits = get_all_pages_with_limit(url, headers, 'Fetching commits', max_pages)
        essential_commits = [{
            'sha': commit['sha'],
            'message': commit['commit']['message'],
            'date': commit['commit']['author']['date'],
            'author': commit['commit']['author']['name']
        } for commit in commits if 'sha' in commit and 'commit' in commit and 'message' in commit['commit'] and 'author' in commit['commit'] and 'date' in commit['commit']['author'] and 'name' in commit['commit']['author']]
        return essential_commits
    except Exception as e:
        print(f'Error: {str(e)}')
        return []

# Example usage
repo_url = "https://github.com/open-covid-19/data"
max_pages = 2
commits = get_commits_with_page_limit(repo_url, max_pages)
with open('commits.json', 'w') as file:
    json.dump(commits, file, indent=4)
