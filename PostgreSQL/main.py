import requests
import json
import os
from dotenv import load_dotenv
from tqdm.auto import tqdm
from urllib.parse import urlparse, urlencode
import customtkinter
import threading
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from time import time
import psycopg2
from psycopg2 import sql
from tkcalendar import DateEntry  # Import DateEntry from tkcalendar

# Load environment variables
load_dotenv()
TOKENS = os.getenv('TOKENS').split(',')
PG_HOST = os.getenv('PG_HOST')
PG_DATABASE = os.getenv('PG_DATABASE')
PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')

current_token_index = 0

# Define authentication headers with the first token
headers = {
    'Authorization': f'token {TOKENS[current_token_index]}',
    'Accept': 'application/vnd.github.v3+json'
}

LOW_LIMIT_THRESHOLD = 1750  # Threshold to trigger token rotation

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=PG_HOST,
    database=PG_DATABASE,
    user=PG_USER,
    password=PG_PASSWORD
)
cursor = conn.cursor()

# Control variable to stop the process
stop_process = False

def rotate_token():
    global current_token_index, headers
    current_token_index = (current_token_index + 1) % len(TOKENS)
    headers['Authorization'] = f'token {TOKENS[current_token_index]}'
    print(f"Rotated to token {current_token_index + 1}")

def get_repo_name(repo_url):
    try:
        path = urlparse(repo_url).path
        repo_name = path.lstrip('/')
        if len(repo_name.split('/')) != 2:
            raise ValueError("Invalid repository URL. Make sure it is in the format 'https://github.com/owner/repo'.")
        return repo_name
    except Exception as e:
        raise ValueError("Error parsing repository URL. Check the format and try again.")

def get_total_pages(url, headers, params=None):
    max_retries = len(TOKENS)
    attempts = 0
    
    while attempts < max_retries:
        try:
            response = requests.get(f"{url}?per_page=1", headers=headers, params=params)
            response.raise_for_status()
            
            # Print rate limit information and rotate token if remaining limit is very low
            rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            print_rate_limit_info(response.headers)
            if rate_limit_remaining < LOW_LIMIT_THRESHOLD:
                print(f"Token limit is low ({rate_limit_remaining} remaining). Rotating token...")
                rotate_token()
                attempts += 1
            else:
                if 'Link' in response.headers:
                    links = response.headers['Link'].split(',')
                    for link in links:
                        if 'rel="last"' in link:
                            last_page_url = link[link.find('<') + 1:link.find('>')]
                            return int(last_page_url.split('=')[-1])
                return 1
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"Token limit reached for token {current_token_index + 1}. Rotating token...")
                rotate_token()
                attempts += 1
            else:
                raise Exception(f'Error fetching data from URL: {url} - {str(e)}')
        except Exception as e:
            raise Exception(f'Unexpected error: {str(e)}')
    raise Exception("All tokens have reached the limit.")

def get_all_pages(url, headers, desc, params=None, date_key=None, start_date=None, end_date=None):
    global stop_process
    results = []

    # Ensure start_date and end_date are datetime.date objects
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date[:10], '%Y-%m-%d').date()

    try:
        total_pages = get_total_pages(url, headers, params)
    except Exception as e:
        print(e)
        return results

    with tqdm(total=total_pages, desc=desc, unit="page") as pbar:
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = []
            for page in range(1, total_pages + 1):
                if stop_process:
                    print("Process stopped by the user.")
                    break
                if params:
                    params['page'] = page
                    full_url = f"{url}?{urlencode(params)}"
                else:
                    full_url = f"{url}?page={page}"
                futures.append(executor.submit(fetch_page_data, full_url, headers, date_key, start_date, end_date))

            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                    pbar.update(1)
                except Exception as e:
                    print(f"Error fetching page data: {str(e)}")

    if not results:
        print(f'No data found for {desc} in the given date range.')

    return results

def fetch_page_data(url, headers, date_key, start_date, end_date):
    global stop_process
    max_retries = len(TOKENS)
    attempts = 0
    
    while attempts < max_retries:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Print rate limit information and rotate token if remaining limit is very low
            rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            print_rate_limit_info(response.headers)
            if rate_limit_remaining < LOW_LIMIT_THRESHOLD:
                print(f"Token limit is low ({rate_limit_remaining} remaining). Rotating token...")
                rotate_token()
                attempts += 1
            else:
                data = response.json()
                if date_key and start_date and end_date:
                    return [item for item in data if start_date <= datetime.strptime(item[date_key], '%Y-%m-%dT%H:%M:%SZ').date() <= end_date]
                return data
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"Token limit reached for token {current_token_index + 1}. Rotating token...")
                rotate_token()
                attempts += 1
            else:
                print(f"Error fetching data from URL: {url} - {str(e)}")
                return []
    print("All tokens have reached the limit.")
    return []

def print_rate_limit_info(headers):
    rate_limit = headers.get('X-RateLimit-Limit')
    rate_limit_remaining = headers.get('X-RateLimit-Remaining')
    rate_limit_reset = headers.get('X-RateLimit-Reset')
    
    reset_time = datetime.fromtimestamp(int(rate_limit_reset)).strftime('%Y-%m-%d %H:%M:%S') if rate_limit_reset else 'N/A'
    print(f"Rate limit: {rate_limit}, Remaining: {rate_limit_remaining}, Reset time: {reset_time}")

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

def get_commits(repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/commits'
    params = {
        'since': f'{start_date}T00:00:01Z',
        'until': f'{end_date}T23:59:59Z',
        'per_page': 35
    }
    commits = get_all_pages(url, headers, 'Fetching commits', params)
    essential_commits = [{
        'sha': commit['sha'],
        'message': commit['commit']['message'],
        'date': commit['commit']['author']['date'], 
        'author': commit['commit']['author']['name']
    } for commit in commits if 'sha' in commit and 'commit' in commit and 'message' in commit['commit'] and 'author' in commit['commit'] and 'date' in commit['commit']['author'] and 'name' in commit['commit']['author']]
    return essential_commits

def get_issues(repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/issues'
    params = {
        'since': f'{start_date}T00:00:01Z',
        'until': f'{end_date}T23:59:59Z',
        'per_page': 35
    }
    issues = get_all_pages(url, headers, 'Fetching issues', params, 'created_at', start_date, end_date)
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

def get_pull_requests(repo_name, headers, start_date, end_date):
    url = f'https://api.github.com/repos/{repo_name}/pulls'
    params = {
        'since': f'{start_date}T00:00:01Z',
        'until': f'{end_date}T23:59:59Z',
        'per_page': 35
    }
    pull_requests = get_all_pages(url, headers, 'Fetching pull requests', params, 'created_at', start_date, end_date)
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

def create_schema_and_tables(repo_name):
    schema_name = repo_name.replace('/', '_').replace('-', '_')
    
    # Create schema
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name)))

    # Create commits table
    cursor.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS {}.commits (
        sha VARCHAR(255) PRIMARY KEY,
        message TEXT,
        date TIMESTAMP,
        author VARCHAR(255)
    )""").format(sql.Identifier(schema_name)))
    
    # Create issues table
    cursor.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS {}.issues (
        number INTEGER PRIMARY KEY,
        title TEXT,
        state VARCHAR(50),
        creator VARCHAR(255),
        comments JSONB
    )""").format(sql.Identifier(schema_name)))
    
    # Create pull_requests table
    cursor.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS {}.pull_requests (
        number INTEGER PRIMARY KEY,
        title TEXT,
        state VARCHAR(50),
        creator VARCHAR(255),
        comments JSONB
    )""").format(sql.Identifier(schema_name)))
    
    # Create branches table
    cursor.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS {}.branches (
        name VARCHAR(255) PRIMARY KEY,
        sha VARCHAR(255)
    )""").format(sql.Identifier(schema_name)))

    conn.commit()

# Função chamada ao clicar no botão "Get Information"
def get_information():
    global stop_process
    stop_process = False  # Reset the control variable
    repo_url = entry_url.get()
    start_date = entry_start_date.get_date()
    end_date = entry_end_date.get_date()

    def collect_data():
        try:
            start_time = time()
            print("Start collecting data...")  # Debug message
            repo_name = get_repo_name(repo_url)
            print(f"Repository name: {repo_name}")  # Debug message
            schema_name = repo_name.replace('/', '_').replace('-', '_')
            
            create_schema_and_tables(repo_name)
            
            # Convert dates to ISO 8601 format with the required time adjustments
            start_date_iso = start_date.strftime('%Y-%m-%d') + 'T00:00:01Z'
            end_date_iso = end_date.strftime('%Y-%m-%d') + 'T23:59:59Z'

            print(f"Start date: {start_date_iso}, End date: {end_date_iso}")  # Debug message

            with ProcessPoolExecutor(max_workers=24) as executor:
                future_commits = executor.submit(get_commits, repo_name, headers, start_date_iso, end_date_iso) if switch_commits.get() == 1 else None
                future_issues = executor.submit(get_issues, repo_name, headers, start_date_iso, end_date_iso) if switch_issues.get() == 1 else None
                future_pull_requests = executor.submit(get_pull_requests, repo_name, headers, start_date_iso, end_date_iso) if switch_pull_requests.get() == 1 else None
                future_branches = executor.submit(get_branches, repo_name, headers) if switch_branches.get() == 1 else None

                if future_commits:
                    commits = future_commits.result()
                    for commit in commits:
                        cursor.execute(sql.SQL("""
                        INSERT INTO {}.commits (sha, message, date, author) 
                        VALUES (%s, %s, %s, %s) ON CONFLICT (sha) DO NOTHING
                        """).format(sql.Identifier(schema_name)),
                        (commit['sha'], commit['message'], commit['date'], commit['author']))
                    conn.commit()
                    print(f"Commits: {len(commits)}")  # Debug message
                    
                if future_issues:
                    issues = future_issues.result()
                    for issue in issues:
                        cursor.execute(sql.SQL("""
                        INSERT INTO {}.issues (number, title, state, creator, comments) 
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (number) DO NOTHING
                        """).format(sql.Identifier(schema_name)),
                        (issue['number'], issue['title'], issue['state'], issue['creator'], json.dumps(issue['comments'])))
                    conn.commit()
                    print(f"Issues: {len(issues)}")  # Debug message
                    
                if future_pull_requests:
                    pull_requests = future_pull_requests.result()
                    for pr in pull_requests:
                        cursor.execute(sql.SQL("""
                        INSERT INTO {}.pull_requests (number, title, state, creator, comments) 
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (number) DO NOTHING
                        """).format(sql.Identifier(schema_name)),
                        (pr['number'], pr['title'], pr['state'], pr['creator'], json.dumps(pr['comments'])))
                    conn.commit()
                    print(f"Pull Requests: {len(pull_requests)}")  # Debug message
                    
                if future_branches:
                    branches = future_branches.result()
                    for branch in branches:
                        cursor.execute(sql.SQL("""
                        INSERT INTO {}.branches (name, sha) 
                        VALUES (%s, %s) ON CONFLICT (name) DO NOTHING
                        """).format(sql.Identifier(schema_name)),
                        (branch['name'], branch['sha']))
                    conn.commit()
                    print(f"Branches: {len(branches)}")  # Debug message

            # Build simplified result message
            message = ""
            if future_commits:
                message += f"Commits: {len(commits)}\n"
            if future_issues:
                message += f"Issues: {len(issues)}\n"
            if future_pull_requests:
                message += f"Pull Requests: {len(pull_requests)}\n"
            if future_branches:
                message += f"Branches: {len(branches)}\n"

            if not message.strip():
                message = "No data found for the given date range."
                print("No data found for the given date range.")
            
            result_label.configure(text=message.strip())
            end_time = time()
            print(f"Data collection completed in {end_time - start_time:.2f} seconds.")  # Debug message

        except ValueError as ve:
            print(f"ValueError: {str(ve)}")  # Debug message
            result_label.configure(text=str(ve))
        except Exception as e:
            print(f"Exception: {str(e)}")  # Debug message
            result_label.configure(text=f"Unexpected error: {str(e)}")
    
    thread = threading.Thread(target=collect_data)
    thread.start()
    

# Função chamada ao clicar no botão "Stop"
def stop_process_function():
    global stop_process
    stop_process = True
    result_label.configure(text="Process stopped by the user.")

# Interface com customtkinter
customtkinter.set_appearance_mode('dark')
customtkinter.set_default_color_theme("dark-blue")

root = customtkinter.CTk()
root.geometry("450x600")
root.title("GitHub Repo Info")

# Set default font using CTkFont
default_font = customtkinter.CTkFont(family="Segoe UI", size=12)

frame = customtkinter.CTkFrame(master=root)
frame.pack(padx=10, pady=10, fill="both", expand=True)

label_url = customtkinter.CTkLabel(master=frame, text="Repository URL", font=default_font)
label_url.pack(pady=12, padx=10)

entry_url = customtkinter.CTkEntry(master=frame, placeholder_text='Enter GitHub repo URL', width=400, font=default_font)
entry_url.pack(pady=12, padx=10)

label_start_date = customtkinter.CTkLabel(master=frame, text="Start Date (DD/MM/YYYY)", font=default_font)
label_start_date.pack(pady=12, padx=10)

entry_start_date = DateEntry(master=frame, date_pattern='dd/MM/yyyy', width=12, background='darkblue', foreground='white', borderwidth=2)
entry_start_date.pack(pady=12, padx=10)

label_end_date = customtkinter.CTkLabel(master=frame, text="End Date (DD/MM/YYYY)", font=default_font)
label_end_date.pack(pady=12, padx=10)

entry_end_date = DateEntry(master=frame, date_pattern='dd/MM/yyyy', width=12, background='darkblue', foreground='white', borderwidth=2)
entry_end_date.pack(pady=12, padx=10)

# Create a frame for the switches and center it
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

button = customtkinter.CTkButton(master=frame, text="Get Information", command=get_information, font=default_font, corner_radius=8)
button.pack(pady=12, padx=10)

stop_button = customtkinter.CTkButton(master=frame, text="Stop", command=stop_process_function, font=default_font, corner_radius=8, fg_color="red")
stop_button.pack(pady=12, padx=10)

result_label = customtkinter.CTkLabel(master=frame, text="", font=default_font)
result_label.pack(pady=12, padx=10)

if __name__ == "__main__":
    root.mainloop()
