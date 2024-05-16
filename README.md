# GitHub Repository Data Miner

## Sobre o Projeto

O GitHub Repository Data Miner é uma ferramenta projetada para extrair e analisar dados detalhados de commits, issues, pull requests e branches de repositórios GitHub. Esta ferramenta é ideal para desenvolvedores, pesquisadores e analistas que desejam obter insights profundos sobre a dinâmica de projetos hospedados no GitHub.

## Funcionalidades

- **Commits**: Extração de informações detalhadas como autor, data e mensagem de commit.
- **Issues**: Análise de abertura, fechamento e discussões de issues para entender tendências e pontos de melhoria.
- **Pull Requests**: Monitoramento de status, revisões e contribuições através de pull requests.
- **Branches**: Visão geral das branches ativas, com detalhes sobre seu uso e contribuições.

## Começando

### Pré-requisitos

Antes de iniciar, certifique-se de que você tem Python 3.8 ou superior instalado em seu sistema. Além disso, você precisará das seguintes bibliotecas Python:

- `requests` para realizar chamadas à API do GitHub
- `pandas` para manipulação e análise de dados
- `matplotlib` para visualização de dados

### Instalação

Siga os passos abaixo para configurar o ambiente e executar a ferramenta:

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/github-repository-data-miner.git
cd github-repository-data-miner

# Instale as dependências necessárias
pip install -r requirements.txt
