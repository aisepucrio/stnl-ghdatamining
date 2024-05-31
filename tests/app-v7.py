import requests
import json
import os
from dotenv import load_dotenv
from tqdm.auto import tqdm
from urllib.parse import urlparse
import customtkinter
import threading
from datetime import datetime

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

# Functions to get repository information
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
    try:
        response = requests.get(f"{url}?per_page=1", headers=headers, params=params)
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
        for page in range(1, total_pages + 1):
            if stop_process:
                print("Process stopped by the user.")
                break
            try:
                if params:
                    params['page'] = page
                    response = requests.get(url, headers=headers, params=params)
                else:
                    response = requests.get(f"{url}?page={page}&per_page=35", headers=headers)
                response.raise_for_status()
                data = response.json()

                if date_key and start_date and end_date:
                    filtered_data = []
                    for item in data:
                        if 'commit' in item:
                            item_date = datetime.strptime(item['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ').date()
                        else:
                            item_date = datetime.strptime(item[date_key], '%Y-%m-%dT%H:%M:%SZ').date()
                        if start_date <= item_date <= end_date:
                            filtered_data.append(item)
                        elif item_date < start_date:
                            break
                    results.extend(filtered_data)
                else:
                    results.extend(data)
                
                pbar.update(1)
            except requests.exceptions.RequestException as e:
                print(f'Error fetching data from URL: {url} with status {e.response.status_code}')
                break
            except Exception as e:
                print(f'Unexpected error fetching data from URL: {url} - {str(e)}')
                break

    if not results:
        print(f'No data found for {desc} in the given date range.')

    return results

def get_comments_with_initial(issue_url, headers, initial_comment, issue_number, start_date, end_date):
    params = {
        'since': start_date,
        'until': end_date
    }
    comments = get_all_pages(issue_url, headers, f'Fetching comments for issue/pr #{issue_number}', params, 'created_at', start_date, end_date)
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
    commits = get_all_pages(url, headers, 'Fetching commits', params, 'commit', start_date, end_date)
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
            comments = get_comments_with_initial(issue_comments_url, headers, initial_comment, issue['number'], start_date, end_date)
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
            comments = get_comments_with_initial(pr_comments_url, headers, initial_comment, pr['number'], start_date, end_date)
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

# Function called when clicking the "Get Information" button
def get_information():
    global stop_process
    stop_process = False  # Reset the control variable
    repo_url = entry_url.get()
    start_date = entry_start_date.get()
    end_date = entry_end_date.get()

    def collect_data():
        try:
            print("Start collecting data...")  # Debug message
            repo_name = get_repo_name(repo_url)
            print(f"Repository name: {repo_name}")  # Debug message
            data = {}

            # Convert dates to ISO 8601 format with the required time adjustments
            start_date_iso = datetime.strptime(start_date, '%d/%m/%Y').strftime('%Y-%m-%d') + 'T00:00:01Z'
            end_date_iso = datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y-%m-%d') + 'T23:59:59Z'

            print(f"Start date: {start_date_iso}, End date: {end_date_iso}")  # Debug message

            if switch_commits.get() == 1:
                commits = get_commits(repo_name, headers, start_date_iso, end_date_iso)
                data['commits'] = commits
                print(f"Commits: {len(commits)}")  # Debug message
            if switch_issues.get() == 1:
                issues = get_issues(repo_name, headers, start_date_iso, end_date_iso)
                data['issues'] = issues
                print(f"Issues: {len(issues)}")  # Debug message
            if switch_pull_requests.get() == 1:
                pull_requests = get_pull_requests(repo_name, headers, start_date_iso, end_date_iso)
                data['pull_requests'] = pull_requests
                print(f"Pull Requests: {len(pull_requests)}")  # Debug message
            if switch_branches.get() == 1:
                branches = get_branches(repo_name, headers)
                data['branches'] = branches
                print(f"Branches: {len(branches)}")  # Debug message

            # JSON file name based on account and repository name
            repo_owner, repo_name_only = repo_name.split('/')
            file_name = f"{repo_owner}_{repo_name_only}_data.json"

            with open(file_name, 'w') as json_file:
                json.dump(data, json_file, indent=4)

            # Build simplified result message
            message = ""
            if 'commits' in data:
                message += f"Commits: {len(data['commits'])}\n"
            if 'issues' in data:
                message += f"Issues: {len(data['issues'])}\n"
            if 'pull_requests' in data:
                message += f"Pull Requests: {len(data['pull_requests'])}\n"
            if 'branches' in data:
                message += f"Branches: {len(data['branches'])}\n"

            if not message.strip():
                message = "No data found for the given date range."
                print("No data found for the given date range.")
            
            result_label.configure(text=message.strip())

        except ValueError as ve:
            print(f"ValueError: {str(ve)}")  # Debug message
            result_label.configure(text=str(ve))
        except Exception as e:
            print(f"Exception: {str(e)}")  # Debug message
            result_label.configure(text=f"Unexpected error: {str(e)}")
    
    thread = threading.Thread(target=collect_data)
    thread.start()

# Function called when clicking the "Stop" button
def stop_process_function():
    global stop_process
    stop_process = True
    result_label.configure(text="Process stopped by the user.")

# Interface with customtkinter
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

entry_start_date = customtkinter.CTkEntry(master=frame, placeholder_text='Enter start date', width=400, font=default_font)
entry_start_date.pack(pady=12, padx=10)

label_end_date = customtkinter.CTkLabel(master=frame, text="End Date (DD/MM/YYYY)", font=default_font)
label_end_date.pack(pady=12, padx=10)

entry_end_date = customtkinter.CTkEntry(master=frame, placeholder_text='Enter end date', width=400, font=default_font)
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

root.mainloop()
