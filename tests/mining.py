import requests
import json
from dotenv import load_dotenv
import os
from tqdm.auto import tqdm
from urllib.parse import urlparse

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('TOKEN')

# Cabeçalhos de autenticação
headers = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# URL base da API do GitHub
BASE_URL = 'https://api.github.com/repos/'

def get_repo_name(repo_url):
    path = urlparse(repo_url).path
    repo_name = path.lstrip('/')
    return repo_name

def get_total_pages(url, headers):
    response = requests.get(f"{url}?per_page=1", headers=headers)
    if response.status_code == 200:
        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            for link in links:
                if 'rel="last"' in link:
                    last_page_url = link[link.find('<') + 1:link.find('>')]
                    return int(last_page_url.split('=')[-1])
        return 1
    else:
        print(f'Erro ao obter dados da URL: {url} com status {response.status_code}')
        return None

def get_all_pages(url, headers, desc):
    results = []
    total_pages = get_total_pages(url, headers)
    if total_pages is None:
        return results

    with tqdm(total=total_pages, desc=desc, unit="page") as pbar:
        for page in range(1, total_pages + 1):
            response = requests.get(f"{url}?page={page}&per_page=100", headers=headers)
            if response.status_code == 200:
                data = response.json()
                results.extend(data)
                pbar.update(1)
            else:
                print(f'Erro ao obter dados da URL: {url} com status {response.status_code}')
                break
    return results

def get_commits(repo_name):
    url = f'{BASE_URL}{repo_name}/commits'
    return get_all_pages(url, headers, 'Fetching commits')

def get_issues(repo_name):
    url = f'{BASE_URL}{repo_name}/issues'
    return get_all_pages(url, headers, 'Fetching issues')

def get_pull_requests(repo_name):
    url = f'{BASE_URL}{repo_name}/pulls'
    return get_all_pages(url, headers, 'Fetching pull requests')

def get_branches(repo_name):
    url = f'{BASE_URL}{repo_name}/branches'
    return get_all_pages(url, headers, 'Fetching branches')

if __name__ == '__main__':
    # URL do repositório do GitHub
    repo_url = 'https://github.com/aisepucrio/jirademo'
    REPO_NAME = get_repo_name(repo_url)

    # Exemplo de uso das funções
    commits = get_commits(REPO_NAME)
    issues = get_issues(REPO_NAME)
    pull_requests = get_pull_requests(REPO_NAME)
    branches = get_branches(REPO_NAME)

    if commits:
        print(f'Commits: o repositório possui {len(commits)} commits')
    if issues:
        print(f'Issues: o repositório possui {len(issues)} issues')
    if pull_requests:
        print(f'Pull Requests: o repositório possui {len(pull_requests)} pull requests')
    if branches:
        print(f'Branches: o repositório possui {len(branches)} branches')

    data = {
        'commits': commits,
        'issues': issues,
        'pull_requests': pull_requests,
        'branches': branches
    }

    # Salvando os dados em um arquivo JSON
    with open('github_repo_data.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

    print('Dados salvos em github_repo_data.json')
