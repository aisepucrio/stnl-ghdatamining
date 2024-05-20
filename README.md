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

Antes de iniciar, certifique-se de que você tem Python 3.8 ou superior instalado em seu sistema. Você também precisará das seguintes bibliotecas Python:

- `requests`: Para realizar chamadas à API do GitHub.
- `json`: Para manipulação de dados em formato JSON.
- `os`: Para interagir com o sistema operacional.
- `dotenv`: Para carregar variáveis de ambiente do arquivo `.env`.
- `tqdm`: Para mostrar barras de progresso em loops.
- `urlparse`: Para analisar URLs.
- `customtkinter`: Para criar interfaces gráficas de usuário.

### Instalação

Siga os passos abaixo para configurar o ambiente e executar a ferramenta:

```bash
# Clone o repositório
git clone https://github.com/aisepucrio/stnl-ghdatamining.git
cd stnl-ghdatamining
```

Crie um arquivo .env no diretório raiz do projeto e adicione seu token pessoal do GitHub no seguinte formato:

TOKEN=coloque_seu_token_aqui
