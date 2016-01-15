from __future__ import print_function
import httplib2
import os
import io
from apiclient import discovery
from apiclient import errors
from apiclient import http
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
    
SCOPES="https://www.googleapis.com/auth/drive" #full access scope
CLIENT_SECRET_FILE="client_secret.json"
APPLICATION_NAME="GoogleDriveTerminal"

def get_credentials():
    """Gets valid user credentials from storage
    If nothing has been stored, of ir the stored credential are invalid,
    the OAuth2 flow is completed to ogtain the new credentials.

    Returns:
    the obtained credential.
    """
    home_dir=os.path.expanduser('~')#homedir='/usr/VuThaiHa
    credential_dir=os.path.join(home_dir,'.credentials')#'/usr/VuThaiHa/.credentials'
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path=os.path.join(credential_dir,'googleDriveTerminal-trial.json')
    store=oauth2client.file.Storage(credential_path)
    credentials=store.get()

    if not credentials or credentials.invalid:
        flow=client.flow_from_clientsecrets(CLIENT_SECRET_FILE,SCOPES)
        flow.user_agent=APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print ('Storing credentials to '+ credential_path)
    return credentials

def get_all_files(service):
    results=service.files().list().execute()
    items=results.get('items',[])
    if not items:
        print ('No files found')
    else:
        print ("Listing all files....")
        for item in items:
            print (item['title']+"        "+item['id'])
            
def list_all_files_in_folder(service,folder_id):
    page_token=None
    while True:
        try:
            param={}
            if page_token:
                param['page_token']=page_token
            children=service.children().list(folderId=folder_id, **param).execute()
            for child in children.get('items',[]):
                f=service.files().get(fileId=child['id']).execute()
                print ('File Title: {0}     File ID: {1}'.format(unicode(f['title']),unicode(f['id'])))
            page_token=children.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError, error:
            print ("An error occurred: %s"%error)
            break
def pwd(service,pwd_id):
    pwd=service.files().get(fileId=pwd_id).execute()
    print (unicode(pwd['title'])+"     "+pwd['id'])

def download(service,file_id):
    request=service.files().get_media(fileId=file_id)
    file_name=service.files().get(fileId=file_id).execute()['title']
    download_folder=os.path.expanduser("~/Downloads")
    download_folder=os.path.join(home,file_name)
    fo=open(download_folder,"a")
    media_request=http.MediaIoBaseDownload(fo,request)
    while True:
        try:
            download_progress,done=media_request.next_chunk()
        except errors.HttpError,error:
            print ("An error occurred: %s"%error)
            return
        if download_progress:
            print ('Download Progress: %d%%'% int(download_progress.progress()*100))
        if done:
            print ("Download Complete")
            return
        
def main():
    credentials=get_credentials()
    http=credentials.authorize(httplib2.Http())
    service=discovery.build('drive','v2',http=http)
    pwd_id='root'
 #   get_all_files(service)
 #   list_all_files_in_folder(service,"root")
    pwd(service,pwd_id)
 #   download(service,'0Bx2aTklRTnmieFAwVEJWSllkRVE')

if __name__=='__main__':
    main()
