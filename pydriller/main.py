from pydriller import Repository
from datetime import datetime
import json

# Caminho para o repositório local ou URL do repositório remoto
repo_path = 'https://github.com/aisepucrio/stnl-ghdatamining'

# Define o intervalo de datas
since_date = datetime(2023, 1, 1)
to_date = datetime(2024, 12, 31)

# Inicializa a análise do repositório com filtro por data
repo = Repository(repo_path, since=since_date, to=to_date)

# Lista para armazenar as informações dos commits
commits_data = []

# Itera sobre os commits do repositório dentro do intervalo de datas
for commit in repo.traverse_commits():
    commit_info = {
        'commit_hash': commit.hash,
        'author': commit.author.name,
        'date': commit.author_date.isoformat(),
        'message': commit.msg,
        'number_of_modified_files': len(commit.modified_files),
        'number_of_lines_added': commit.insertions,
        'number_of_lines_deleted': commit.deletions
    }
    commits_data.append(commit_info)

# Caminho para o arquivo JSON
json_file_path = 'commits_data.json'

# Salva as informações dos commits em um arquivo JSON
with open(json_file_path, 'w') as json_file:
    json.dump(commits_data, json_file, indent=4)

print(f'Informações dos commits salvas em {json_file_path}')
