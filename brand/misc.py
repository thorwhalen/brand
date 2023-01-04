"""Misc tools"""

import requests


def github_org_name_available(name):
    r = requests.get(f'https://www.github.com/{name}')
    if r.status_code != 200:
        return True
    return False


def search_for_available_github_org_names(candidates, verbose=True):
    for i, name in enumerate(candidates):
        if github_org_name_available(name):
            if verbose:
                print(f'\n--> {name}\n')
            yield name
        else:
            if verbose:
                print(f'({i}) {name}', end=', ')
