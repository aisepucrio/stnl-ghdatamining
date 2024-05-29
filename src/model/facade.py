import requests

class Facade:
    def __init__(self):
        self._model = Model()

    def get_url_response(self, url):
        response = requests.get(url, headers=self.headers)
        response.raise_for_status() # To-Do: check if it is necessary
        return (response, response.status_code) # in this way you can check the status code anywhere
    
    def test_repo_name(self, repo_name):
        assert len(repo_name.split('/')) == 2, "Invalid repository name URL."
    
