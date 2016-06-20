#!/usr/bin/env python
"""
Set expense folder permissions for GDG NA chapters

Relies heavily on the samples at
https://developers.google.com/drive/v3/web/quickstart/python and
https://developers.google.com/drive/v3/web/search-parameters
"""

import httplib2
import os
import requests

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'GDG Expense Folder Permissions'

class GDG:
    """Holds GDG chapter info"""

    def __init__(self, name, gplus):
        self.name = name
        self.gplus = gplus
        self.leads = []
        self.expense_folder = None

    def set_expense_folder(self, folder_id):
        """The Google Drive file ID for the chapter's expense folder"""
        self.expense_folder = folder_id

    def set_leads(self, leads):
        """An array of email addresses for chapter leads"""
        self.leads = leads

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'expense_folder_permissions.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_gdgs():
    """Get the list of GDGs from dev directory

    Returns:
        gdgs, a list of GDGs
    """

    gdgs = {}
    r = requests.get('https://developers.google.com/groups/directorygroups/')
    r.raise_for_status()
    for x in r.json()['groups']:
        if x['country'] in ['Canada', 'United States']:
            gdg = GDG(x['name'], x['gplus_id'])
            # XXX get leads here, see https://github.com/gdg-x/hub/blob/5546cfdf7e09bbb8f7b91ba5d3e61b2a45fbedb1/lib/clients/devsite.js#L67
            gdgs[x['name']] = gdg

    return gdgs

def get_expense_folder(service):
    """Gets the ID of the expense folder

    We need this to retrieve the list of subfolders
    """

    # short circuit because we only need to get this once
    return '0B7PTC3UtA5dEUzhuVE5hQ2VzV3c'

    page_token = None
    response = service.files().list(q="mimeType='application/vnd.google-apps.folder' and 'momander@google.com' in owners and name='GDG/Expert uploaded receipts'",
                                         spaces='drive',
                                         fields='nextPageToken, files(id, name)',
                                         pageToken=page_token).execute()
    folder = response.get('files', [])
    return folder[0].get('id')

def get_gdg_expense_folders(service, root):
    """Gets the set of subfolders for each GDG, as well as GDEs

    Returns:
        folders, the folder names and IDs
    """

    folders = []
    while True:
        page_token = None
        response = service.files().list(q="mimeType='application/vnd.google-apps.folder' and 'momander@google.com' in owners and '%s' in parents" % (root),
                                             spaces='drive',
                                             fields='nextPageToken, files(id, name)',
                                         pageToken=page_token).execute()
        for folder in response.get('files', []):
            folders.append({'name': folder.get('name'), 'id': folder.get('id')})
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            return folders

def update_gdg_folders(gdgs, folders):
    """Sets the expense folder ID for each GDG"""

    for folder in sorted(folders, key=lambda folder: folder['name']):
        if folder['name'] in gdgs:
            gdgs[folder['name']].set_expense_folder(folder['id'])
            print("%s %s" % (folder['name'], folder['id']))
        else:
            print("No GDG with name '%s'!" % (folder['name']))

def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    gdgs = get_gdgs()
    root = get_expense_folder(service)
    folders = get_gdg_expense_folders(service, root)
    update_gdg_folders(gdgs, folders)

if __name__ == '__main__':
    main()
