# This file holds function definitions that I felt would unnecessarily
# clutter the main notebook

import os
import requests
import pandas as pd
# for download progress bar
from tqdm import tqdm
# for parsing out the filename from content-disposition
import pyrfc6266
from ldaca.ldaca import LDaCA

def download(url, filepath, API_TOKEN=None):
    if not API_TOKEN:
        raise Exception("missing API token")
    print('downloading')
    response = requests.get(
        url,
        stream=True,
        allow_redirects=True,
        headers={'Authorization': 'Bearer ' + API_TOKEN}
    )

    # Sizes in bytes.
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024

    with tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar:
        with open(filepath, "wb") as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

def find_license_for_file(ldaca, file_entity):
    # [e for e in ldaca.crate.get_entities()]
    parents = file_entity.get("@reverse").get('hasPart')
    if len(parents) > 1:
        raise Exception(f"Didn't expect a file to exist in multiple collections ({file_entity.id})")
    parent_id = file_entity.get("@reverse").get('hasPart')[0].get('@id')
    return ldaca.crate.get(parent_id).get('license')


def download_file(ldaca, file_entity, force = False, API_TOKEN=None):
    if not API_TOKEN:
        raise Exception("missing API token")
    if not file_entity:
        raise Exception(f"{file_entity} is None")
    if not 'File' in file_entity.get("@type", []):
        raise Exception(f"Tried to download {file_entity.get('@id')}, but it does not have type File")

    # TODO: move magic string
    cwd = os.getcwd()
    folder = os.path.join(cwd, "data")

    head_response = requests.head(
        file_entity.get('@id'),
        allow_redirects=True,
        headers={'Authorization': 'Bearer ' + API_TOKEN}
    )

    filename = pyrfc6266.parse_filename(head_response.headers['content-disposition'])
    print(filename, end=' ')

    # TODO: handle if there's multiple licenses
    # TODO: also if there are multiple names
    licensename = find_license_for_file(ldaca, file_entity)[0].get('name')[0]
    if not os.path.exists(os.path.join(folder, licensename)):
        os.mkdir(os.path.join(folder, licensename))
        # TODO: download license file
        # download(find_license_for_file(file_entity)[0].get('id'), filepath)

    filepath = os.path.join(folder, licensename, filename)

    if os.path.exists(filepath) and not force:
        # TODO: check its the right size
        expected = int(head_response.headers.get("content-length", 0))
        actual = os.path.getsize(filepath)
        if expected == actual:
            print('already downloaded')
            return filepath
        else:
            print(f'exists but unexpected size, deleting ({expected} != {actual})', end=' ')
            os.remove(filepath)
    elif os.path.exists(filepath) and force:
        # TODO: delete existing
        print('exists but `force=True`, deleting', end=' ')
        os.remove(filepath)
        pass

    print('downloading')
    download(file_entity.get('@id'), filepath, API_TOKEN=API_TOKEN)