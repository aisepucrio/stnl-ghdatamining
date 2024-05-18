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
    try:
        path = urlparse(repo_url).path
        repo_name = path.lstrip('/')
        if len(repo_name.split('/')) != 2:
            raise ValueError("URL do repositório inválida. Certifique-se de que está no formato 'https://github.com/owner/repo'.")
        return repo_name
    except Exception as e:
        raise ValueError("Erro ao analisar a URL do repositório. Verifique o formato e tente novamente.")

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
            raise ValueError("Repositório não encontrado.")
        elif e.response.status_code == 401:
            raise ValueError("Token inválido ou expirado.")
        elif e.response.status_code == 403:
            raise ValueError("Limite de requisições atingido.")
        else:
            raise Exception(f'Erro ao obter dados da URL: {url} com status {e.response.status_code}')
    except Exception as e:
        raise Exception(f'Erro inesperado: {str(e)}')

def get_all_pages(url, headers, desc):
    results = []
    try:
        total_pages = get_total_pages(url, headers)
    except Exception as e:
        print(e)
        return results

    with tqdm(total=total_pages, desc=desc, unit="page") as pbar:
        for page in range(1, total_pages + 1):
            try:
                response = requests.get(f"{url}?page={page}&per_page=100", headers=headers)
                response.raise_for_status()
                data = response.json()
                results.extend(data)
                pbar.update(1)
            except requests.exceptions.RequestException as e:
                print(f'Erro ao obter dados da URL: {url} com status {e.response.status_code}')
                break
            except Exception as e:
                print(f'Erro inesperado ao obter dados da URL: {url} - {str(e)}')
                break
    return results

def get_comments_with_initial(issue_url, headers, initial_comment, issue_number):
    comments = get_all_pages(issue_url, headers, f'Fetching comments for issue/pr #{issue_number}')
    essential_comments = [{
        'user': initial_comment['user']['login'],
        'body': initial_comment['body'],
        'created_at': initial_comment['created_at']
    }]
    essential_comments.extend([{
        'user': comment['user']['login'],
        'body': comment['body'],
        'created_at': comment['created_at']
    } for comment in comments if 'user' in comment and 'login' in comment['user'] and 'body' in comment and 'created_at' in comment])
    return essential_comments

def get_commits(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/commits'
    commits = get_all_pages(url, headers, 'Fetching commits')
    essential_commits = [{
        'sha': commit['sha'],
        'message': commit['commit']['message'],
        'date': commit['commit']['author']['date'],
        'author': commit['commit']['author']['name']
    } for commit in commits if 'sha' in commit and 'commit' in commit and 'message' in commit['commit'] and 'author' in commit['commit'] and 'date' in commit['commit']['author'] and 'name' in commit['commit']['author']]
    return essential_commits

def get_issues(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/issues'
    issues = get_all_pages(url, headers, 'Fetching issues')
    essential_issues = []
    for issue in issues:
        if 'number' in issue and 'title' in issue and 'state' in issue and 'user' in issue and 'login' in issue['user']:
            issue_comments_url = issue['comments_url']
            initial_comment = {
                'user': issue['user'],
                'body': issue['body'],
                'created_at': issue['created_at']
            }
            comments = get_comments_with_initial(issue_comments_url, headers, initial_comment, issue['number'])
            essential_issues.append({
                'number': issue['number'],
                'title': issue['title'],
                'state': issue['state'],
                'creator': issue['user']['login'],
                'comments': comments
            })
    return essential_issues

def get_pull_requests(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/pulls'
    pull_requests = get_all_pages(url, headers, 'Fetching pull requests')
    essential_pull_requests = []
    for pr in pull_requests:
        if 'number' in pr and 'title' in pr and 'state' in pr and 'user' in pr and 'login' in pr['user']:
            pr_comments_url = pr['_links']['comments']['href']
            initial_comment = {
                'user': pr['user'],
                'body': pr['body'],
                'created_at': pr['created_at']
            }
            comments = get_comments_with_initial(pr_comments_url, headers, initial_comment, pr['number'])
            essential_pull_requests.append({
                'number': pr['number'],
                'title': pr['title'],
                'state': pr['state'],
                'creator': pr['user']['login'],
                'comments': comments
            })
    return essential_pull_requests

def get_branches(repo_name, headers):
    url = f'https://api.github.com/repos/{repo_name}/branches'
    branches = get_all_pages(url, headers, 'Fetching branches')
    essential_branches = [{
        'name': branch['name'],
        'sha': branch['commit']['sha']
    } for branch in branches if 'name' in branch and 'commit' in branch and 'sha' in branch['commit']]
    return essential_branches

# Função chamada ao clicar no botão "Obter Informações"
def obter_informacoes():
    repo_url = entry_url.get()
    try:
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

    except ValueError as ve:
        result_label.configure(text=str(ve))
    except Exception as e:
        result_label.configure(text=f"Erro inesperado: {str(e)}")

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
