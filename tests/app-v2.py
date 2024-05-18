import requests
import json
import os
from dotenv import load_dotenv
from tqdm.auto import tqdm
from urllib.parse import urlparse
import customtkinter

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('TOKEN')

# Defina os cabeçalhos de autenticação
headers = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Funções para obter informações do repositório
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

def get_commits(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/commits'
    commits = get_all_pages(url, headers, 'Fetching commits')
    essential_commits = [{
        'sha': commit['sha'],
        'message': commit['commit']['message'],
        'date': commit['commit']['author']['date'],
        'author': commit['commit']['author']['name']
    } for commit in commits]
    return essential_commits

def get_issues(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/issues'
    issues = get_all_pages(url, headers, 'Fetching issues')
    essential_issues = [{
        'number': issue['number'],
        'title': issue['title'],
        'state': issue['state'],
        'creator': issue['user']['login']
    } for issue in issues]
    return essential_issues

def get_pull_requests(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/pulls'
    pull_requests = get_all_pages(url, headers, 'Fetching pull requests')
    essential_pull_requests = [{
        'number': pr['number'],
        'title': pr['title'],
        'state': pr['state'],
        'creator': pr['user']['login']
    } for pr in pull_requests]
    return essential_pull_requests

def get_branches(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/branches'
    branches = get_all_pages(url, headers, 'Fetching branches')
    essential_branches = [{
        'name': branch['name'],
        'sha': branch['commit']['sha']
    } for branch in branches]
    return essential_branches

# Função chamada ao clicar no botão "Obter Informações"
def obter_informacoes():
    repo_url = entry_url.get()
    repo_name = get_repo_name(repo_url)
    data = {}
    
    if switch_commits.get() == 1:
        data['commits'] = get_commits(repo_name, headers)
    if switch_issues.get() == 1:
        data['issues'] = get_issues(repo_name, headers)
    if switch_pull_requests.get() == 1:
        data['pull_requests'] = get_pull_requests(repo_name, headers)
    if switch_branches.get() == 1:
        data['branches'] = get_branches(repo_name, headers)

    # Nome do arquivo JSON baseado na conta e nome do repositório
    repo_owner, repo_name_only = repo_name.split('/')
    file_name = f"{repo_owner}_{repo_name_only}_data.json"

    with open(file_name, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    # Construir mensagem de resultado simplificada
    message = ""
    if 'commits' in data:
        message += f"Commits: {len(data['commits'])}\n"
    if 'issues' in data:
        message += f"Issues: {len(data['issues'])}\n"
    if 'pull_requests' in data:
        message += f"Pull Requests: {len(data['pull_requests'])}\n"
    if 'branches' in data:
        message += f"Branches: {len(data['branches'])}\n"

    result_label.configure(text=message.strip())

# Interface com customtkinter
customtkinter.set_appearance_mode('dark')
customtkinter.set_default_color_theme("dark-blue")

root = customtkinter.CTk()
root.geometry("450x500")
root.title("GitHub Repo Info")

# Definir a fonte padrão usando CTkFont
default_font = customtkinter.CTkFont(family="Segoe UI", size=12)

frame = customtkinter.CTkFrame(master=root)
frame.pack(padx=10, pady=10, fill="both", expand=True)

label_url = customtkinter.CTkLabel(master=frame, text="Repository URL", font=default_font)
label_url.pack(pady=12, padx=10)

entry_url = customtkinter.CTkEntry(master=frame, placeholder_text='Enter GitHub repo URL', width=400, font=default_font)
entry_url.pack(pady=12, padx=10)

# Criar um frame para os switches e centralizá-lo
switch_frame = customtkinter.CTkFrame(master=frame)
switch_frame.pack(pady=12, padx=10, anchor='center', expand=True)

switch_commits = customtkinter.CTkSwitch(master=switch_frame, text="Commits", font=default_font)
switch_commits.pack(pady=5, padx=20, anchor='w')
switch_issues = customtkinter.CTkSwitch(master=switch_frame, text="Issues", font=default_font)
switch_issues.pack(pady=5, padx=20, anchor='w')
switch_pull_requests = customtkinter.CTkSwitch(master=switch_frame, text="Pull Requests", font=default_font)
switch_pull_requests.pack(pady=5, padx=20, anchor='w')
switch_branches = customtkinter.CTkSwitch(master=switch_frame, text="Branches", font=default_font)
switch_branches.pack(pady=5, padx=20, anchor='w')

button = customtkinter.CTkButton(master=frame, text="Obter Informações", command=obter_informacoes, font=default_font)
button.pack(pady=12, padx=10)

result_label = customtkinter.CTkLabel(master=frame, text="", font=default_font)
result_label.pack(pady=12, padx=10)

root.mainloop()
