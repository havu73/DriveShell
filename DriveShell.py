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
from idReference import idReference as idR
from apiclient.http import MediaFileUpload
name_id={}
id_name_parents={}

    
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


def initialize_dictionaries(service):
    '''
    Initialize id_name_parents and name_id dictionaries
    These two dictionaries are data in memory that helps traveser the path
    of any given file/directory. The in-memory data increases efficiency, especially
    when a  lot of commands are processed,
    requiring to find IDs of a lot of files/directores
    '''
    root=service.files().get(fileId='root').execute()
    name_id[root['title']]=[root['id']]
    id_name_parents[root['id']]=idR(root['id'],"My Drive",None)
    results=service.files().list(q="trashed=false",
                                         spaces='drive',
                                         fields='items(id,title,parents,mimeType)').execute()
    items=results.get('items',[])
    if not items:
        print ('No files exist in your drive')
    else:
        for item in items:
            fileID=item['id']
            fileName=item['title']
            if not (name_id.has_key(fileName)):
                name_id[fileName]=[fileID]
            else:
                name_id[fileName].append(fileID)

            parent_list=item['parents']
            fileParents=[]
            for parent in parent_list:
                fileParents.append(parent['id'])
            id_name_parents[fileID]=idR(fileID,fileName,fileParents)

        
def traverse_path(path, fileID):
    '''
    @param: path: path of a folder processed into list
                    fileID: the file ID of a file
    @return: True if the path represents a parent folder of the file
    that has fileID
    Ex: FileID of 'My Drive/Folder1/Folder2' is x
    -->traverse_path(["My Drive","Folder1"],x) will return True
    '''
    dirName=path[-1]
    
    if not dirName in name_id:
        return False
    
    parent_id=name_id[dirName]
    if len(parent_id)>1:###Based on my experience, there is no case
        # when a child has multiple parent
        return False
    child_parent=id_name_parents[fileID].getParents()
    if parent_id[0] in child_parent:
        if path[-1]=='My Drive' and len(path)==1:
            return True
        elif len(path)==1 and path[-1]!="My Drive":
            return False
        else:
            return traverse_path(path[:-1],parent_id[0])
    else:
        return False
    
def findID(path):
    """
    @param: the path of the file. Note that this function right now can only process
    complete path, i.e path that starts with 'My Drive'.
    Ex: "My Drive/Folder1" or "My Drive/upload.png"
    @return: fileID (string) of the file/directory referred to by path
    
    """
    directories=path.split('/')
    fileName=directories[-1]
    if not fileName in name_id:
        print ("No such file or directory: "+path)
        return None
    
    fileID=name_id[directories[-1]]
    
    if len(directories)==1 and len(fileID)==1:
        return fileID[0]
    elif len(directories)==1 and len(fileID)>1:
        return None
    
    result=None
    for item in fileID:
        if traverse_path(directories[:-1],item)==True:
            return item
    ## could not find an id that matches the given path
    print ("No such file or directory: "+path)
    return None

def list_file(service, fID):
    '''
    @param: service
        fID: file Id of the directory to list files from
    @return: None. Print out the name and ID of files and directories in the provided directory
    '''
    children=service.files().list(q="'%s' in parents and trashed=false"%fID
                                     ,spaces="drive"
                                     ,fields="items(title,id)").execute()
    
    for child in children['items']:
        print (child['title']+"   "+child['id'])


def list_file_recursive(service,fID,space):
    '''
    @param: service
                    fID: ID of the directory to list files directly in the directory and files in subdirectories
                    in the provided directory
                    space: how many space characters to indent when printing files
    @return: None. print out a recursive list of files inside the specified directory and its subdirectories
    '''
    #print (fID)
    files=service.files().list(q="'%s' in parents and trashed=false"%fID,
                                  spaces="drive",
                                  fields="items(title,id,mimeType)").execute()
    children=files['items']
    results=[]
    for child in children:
        print (" "*space+child['title']+"   "+child['id'])
        if child["mimeType"]=="application/vnd.google-apps.folder":
            list_file_recursive(service,child['id'],space+5)
            
def download(service,file_name,file_id,path):
    '''
    @param: service
                    file_name: the local name of the downloaded file (ex: 'download_file.extension')
                    file_id: the id of the file to download
                    path: the local path of directory that contains the downloaded file
    @return: None. Download the file from Google Drive to a local directory
    '''
    request=service.files().get_media(fileId=file_id)
    download_dest=os.path.join(path,file_name)
    fo=open(download_dest,"a")
    media_request=http.MediaIoBaseDownload(fo,request)
    while True:
        try:
            download_progress,done=media_request.next_chunk()
        except errors.HttpError,error:
            print("an error occurred: %s"%error)
            return
        if download_progress:
            print('Download Progress: %d%%'% int(download_progress.progress()*100))
        if done:
            print ("Download Complete")
            return
        
def add_id_name_parents(fileID,name,parent):
    '''
    @param: fileID: file id of the file to be added into id_name_parents dictionary
                    name: name of the file to be added
                    parent: id (string) of the parent directory of the file in Google Drive
    @return: add an entry to the id_name_parents dictionary.
    This function is called when a file is uploaded into Google Drive
    '''
    if not (fileID in id_name_parents):
        id_name_parents[fileID]=idR(fileID,name,[parent])
    else:
        id_name_parents[fileID].add_parent(parent)

def add_name_id(fileID,name):
    '''
    @param: fileID: file id (string)of the file to be added into name_id dictionary
                    name: name of the file to be added
    @return: add an entry to the name_id dictionary.
    This function is called when a file is uploaded, or copied into Google Drive
    '''
    if not (name in name_id):
        name_id[name]=[fileID]
    else:
        name_id[name].append(fileID)
        
def upload(service,file_path,folder_id,file_name):
    '''
    @param: service
                    file_path: the local path to the file to be uploaded (Ex: '/Users/UserName/Desktop/upload.png')
                    folde_id: the id of the folder that will contain the uploaded file
                    file_name: the name of the file to be uploaded, or copied into Google Drive (ex: uploaded.png)
    @return: None. upload a file into Google Drive
    '''
    media_body=MediaFileUpload(file_path,resumable=True)
    body={"title":file_name,
          "parents":[{"id":folder_id}]}
    try:
        upload=service.files().insert(body=body,
                                      media_body=media_body).execute()
        uploadID=upload['id']
        upload_name=upload['title']
        add_id_name_parents(uploadID,upload_name,folder_id)
        add_name_id(uploadID, upload_name) 
        return upload
    except errors.HttpError,error:
        print ("An error occurred: %s"%error)
        return None

def copy(service,original_file_id,parent_id,copy_title):
    '''
    @param: service
                    original_file_id: id of file to be copied
                     parent_id: id of the folder that contains the newly-copied file. 
                    copy_title: the name of the newly_copied file(ex: uploaded.png)
    @return: None. copy a file into another folder in Google Drive
    '''
    body={"title": copy_title,
                 "parents":[{"id":parent_id}]}
    try:
        copied_file=service.files().copy(fileId=original_file_id, body=body).execute()
        #print (copied_file['id'])
        
        copy_id=copied_file['id']
        copy_name=copy_title
        add_id_name_parents(copy_id,copy_name,parent_id)
        add_name_id(copy_id,copy_name)           
    except errors.HttpError, error:
        print ('(An error occurred: %s'%error)
        return None
    
def delete_id_name_parents(file_id):
    '''
    @param: id of the file to be deleted
    @return: delete an entry from id_name_parents dictionary
    '''
    del(id_name_parents[file_id])

def delete_name_id(name):
    '''
    @param: name of the file to be deleted
    @return: delete an entry from name_id dictionary
    '''
    del(name_id[name])
    
def delete(service,delete_id):
    '''
    @param: service
    delete_id: file id of the file to be deleted
    @return: delete a file from Google Drive
    '''
    try:
        delete_o=service.files().get(fileId=delete_id).execute()
        children_id=[]
        if delete_o['mimeType']=='application/vnd.google-apps.folder':
            children=service.children().list(folderId=delete_id).execute()
            for child in children['items']:
                children_id.append(child['id'])

        service.files().delete(fileId=delete_id).execute()
        
        if len(children_id)!=0:
            for child in children_id:
                delete_name=id_name_parents[child].getName()
                delete_name_id(delete_name)
                delete_id_name_parents(child)
        
        delete_name=id_name_parents[delete_id].getName()
        delete_name_id(delete_name)
        delete_id_name_parents(delete_id)
        print ("Deleted successfully")
    except errors.HttpError,error:
        print ("An error occurred: %s"%error)

def list_share(service,file_id):
    '''
    @param: service
    delete_id: file id of the file whose info about shares will be listed
    @return: list the name, role and email address of people who have access to the file
    '''
    try:
        permissions=service.permissions().list(fileId=file_id).execute()
        if permissions==None:
            print ("No files exist in your Google Drive yet")
            return
        print ("Permissions for file with ID: "+file_id)
        for thing in permissions['items']:
            if thing['name']!=None:
                print (thing['name']+"   "+thing['role']+"   "+thing['emailAddress'])
            else:
                print (thing['role']+"   "+thing['emailAddress'])
    except errors.HttpError, error:
        print ('An error occurred: %s' % error)
    return None


def insert_share_notif(service,file_id,message,role,per_type,value):
    '''
    @param: service
    file_id: id of the file to be shared
    message: (string) content of invitation email
    role: (string) one of four options: owner, reader, writer, commenter.
    per_type: (string) can be one of the following: user, group, domain, anyone
    value: name defined in Google drive account or email address of the person to share the file with
    @return: share a file with an invitation email
    '''
    insert_body={'value':value,'type':per_type,'role':role}
    try: 
        permission=service.permissions().insert(fileId=file_id,body=insert_body,
                                     emailMessage=message,sendNotificationEmails=True)
        if permission!=None:
            print("Shared successfully")
    except errors.HttpError,error:
        print ("An error occurred: %s"%error)
    return None

def insert_share(service,file_id,role,per_type,value):
    '''
    @param: service
    file_id: id of the file to be shared
    role: (string) one of four options: owner, reader, writer, commenter.
    per_type: (string) can be one of the following: user, group, domain, anyone
    value: name defined in Google drive account or email address of the person to share the file with
    @return: share a file without an invitation email
    '''
    insert_body={'value':value,
                 'type':per_type,
                 'role':role}
    try:
        permission=service.permissions().insert(fileId=file_id,body=insert_body)
        if permission!=None:
            print ("Shared successfully")
    except errors.HttpError,error:
        print ("An error occurred: %s"%error)
    return None
    

def process_list(service,command,commands):
    '''
    @param:
    service
    command: the original user command starting with "ls" or "list"
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, find folder ID and call the list_files function if the command is verified as valid
    '''
    if len(commands)>3:
        print ("Invalid command: "+command)
        print ("Please make sure to follow the calling protocol")
        print ("To list file: \"ls -r 'folder_path'\"")
        print ("You can skip the '-r' flag")
        return
    if len(commands)==1:
        list_file(service, "root")
        return
    elif len(commands)==2:
        if commands[1]=="-r":
            list_file_recursive(service,"root",0)
            return
        else:
            folderID=findID(commands[1])
            if folderID==None:
                return#user is informed in findID function
            else:
                folder=service.files().get(fileId=folderID).execute()
                if (folder['mimeType']!='application/vnd.google-apps.folder'):
                    print("The provided path is not a folder")
                    return
                list_file(service,folderID)
                return
    else:
        if commands[1]!="-r":
            print ("Invalid command: "+command)
            print ("List function only supports '-r' flag")
            return
        folderID=findID(commands[2])
        if folderID==None:
            return#user is informed in findID function
        else:
            folder=service.files().get(fileId=folderID).execute()
            if (folder['mimeType']!='application/vnd.google-apps.folder'):
                print("The provided path is not a folder")
                return
            else:
                list_file_recursive(service,folderID,0)
                return

def process_upload(service,command,commands):
    '''
    @param:
    service
    command: the original user command starting with "upload" 
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, identify different parameters to be passed into upload funciton
    and call the upload function if the command is verified as valid
    @valid_command_format:
    1, upload -n 'file_name' 'local_path' 'drive_path'
    2, upload 'local_path'
    3, upload 'local_path' 'drive_path'
    '''
    length=len(commands)
    if not (length==2 or length==3 or length==5):
        print ("Invalid command: "+command)
        print ("Please make sure that you followed the command protocol")
        print ("To upload file: upload -n 'file_name' 'local_path' 'drive_path'")
        print ("You may skip '-n' 'file_name' or 'drive_path' or both")
        return
    if length==5 and commands[1]!="-n":
        print ("Invalid command: "+ command)
        print ("Upload function right now only supports '-n' flag")
        return
    if length==2:
        local_path=os.path.expanduser("~")
        local_path=os.path.join(local_path,commands[1])
        if not os.path.isfile(local_path):
            print ("Invalid command: "+command)
            print ("File path in local computer does not exists or is not a regular file")
            return
        file_name=local_path.split("/")[-1]
        upload(service,local_path,"root",file_name)
        return

    #local_path
    local_path=os.path.expanduser("~")
    local_path=os.path.join(local_path,commands[-2])
    if not os.path.isfile(local_path):
        print ("Invalid command: "+command)
        print("File path in local computer does not exits or it is not a regular file")
        return

    #drive_path
    drive_name=commands[-1]
    folderID=findID(drive_name)
    if (folderID ==None):
        print ("Invalid command: "+command)
        print ("File in Google Drive does not exist")
        return
    folder=service.files().get(fileId=folderID).execute()
    if folder['mimeType']!="application/vnd.google-apps.folder":
        print("Invalid command: "+command)
        print ("Google Drive Path is not a folder")
        return

    if length==5:
        upload(service,local_path,folderID,commands[2])#commands[2]->fileName
        return
    else:
        file_name=local_path.split("/")[-1]
        upload(service,local_path,folderID,file_name)
        return

def process_download(service,command,ls):
    '''
    @param:
    service
    command: the original user command starting with "download" 
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, identify different parameters to be passed into download funciton
    and call the download function if the command is verified as valid
    @valid_command_format:
    1, download -n 'file_name' 'drive_path' 'local_path'
    2, download 'drive_path'
    3, download -n 'file_name' 'drive_path'
    4, download 'drive_path' 'local_path'
    '''
    length=len(ls)
    if not (length==3 or length==2 or length==5 or length==4):
        print ("Invalid command: "+command)
        print ("Please make sure that you followed the command protocol")
        print ("To download file: download -n 'file_name' 'drive_path' 'local_path'")
        print ("You may skip '-n' 'file_name' or 'local_path' or both")
        return
    if (length==5 or length==4) and ls[1]!='-n':
        print ("Invalid command: "+command)
        print ("Download function only supports '-n' flag")
        return

    # process local_path and drive_path
    if length==2 or length==4:
        local_name="Downloads"
        drive_name=ls[-1]
    else:
        local_name=ls[-1]
        drive_name=ls[-2]

    local_path=os.path.expanduser("~")
    local_path=os.path.join(local_path, local_name)
    if not os.path.isdir(local_path):
        print ("Invalid command: "+command)
        print("Local path must be a directory")
        print (local_path)
        return

    file_id=findID(drive_name)
    if file_id==None:
        print ("Invalid command: "+command)
        print ("No such file in Google Drive")
        return
    file_o=service.files().get(fileId=file_id).execute()
    if file_o['mimeType']=='application/vnd.google-apps.folder':
        print ("Invalid command: "+command)
        print ("Cannot download a Google Drive folder")
        return
    
    if length==2 or length==3:
        file_name=drive_name.split("/")[-1]
    else:
        file_name=ls[2]

    download(service,file_name,file_id,local_path)
    return

def process_copy(service,command,ls):
    '''
    @param:
    service
    command: the original user command starting with "copy" 
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, identify different parameters to be passed into copy funciton
    and call the copy function if the command is verified as valid
    @valid_command_format:
    1, copy -n 'file_name' 'original_file_path' 'copy_file_path'
    2, download 'original_file_path' 'copy_file_path'
    3, download 'original_file_path' 
    '''
    length=len(ls)
    if not (length==2 or length==5 or length==3):
        print ("Invalid command: "+ command)
        print ("Please make sure that you follow the command protocol")
        print ("To copy a file: copy -n 'file_name' 'original_file_path' 'copy_file_path'")
        print ("You can skip the '-n 'file_name'' flag or 'copy_file_path' or both")
        return

    if length==3 or length==5:
        original_name=ls[-2]
        copy_name=ls[-1]
    if length==2:
        original_name=ls[-1]
        last_index=original_name.rfind("/")
        copy_name=original_name[:last_index]

    original_id=findID(original_name)
    if original_id==None:
        return
    original_file=service.files().get(fileId=original_id).execute()
    if original_file['mimeType']=='application/vnd.google-apps.folder':
        print ("Invalid command: "+command)
        print ("The original file is a folder. We cannot copy a folder")
        return

    copy_id=findID(copy_name)
    if copy_id==None:
        return
    copy_folder=service.files().get(fileId=copy_id).execute()
    if copy_folder['mimeType']!='application/vnd.google-apps.folder':
        print ("Invalid command: "+command)
        print("The copy_path needs to refer to a folder")
        return
    if length==5:
        index=original_name.rfind("/")
        original_folder_name=original_name[:index]
        if original_folder_name==copy_name:
            file_name=original_name[index+1:]
            if file_name==ls[2]:
                print ("Command: "+command)
                print ("We do not copy  a file into the same folder with the same filename")
                print ("If you still want to process the command, please visit your google drive and do it manually")
                return

    if length==5:
        file_name=ls[2]
    else:
        index=original_name.rfind("/")
        o_name=original_name[index+1:]
        file_name="CopyOf"+o_name

    copy(service,original_id,copy_id,file_name)


def process_delete(service,command,ls):
    '''
    @param:
    service
    command: the original user command starting with "delete" 
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, identify different parameters to be passed into copy funciton
    and call the delete function if the command is verified as valid
    @valid_command_format:
    1, copy 'file_path'
    '''
    if len(ls)!=2:
        print ("Invalid command: "+command)
        print ("Please make sure you follow the command protocol")
        print ("To delete file: delete 'file_name'")
        return

    file_id=findID(ls[1])
    if file_id==None:
        return
    delete(service,file_id)

def process_share(service,command,ls):
    '''
    @param:
    service
    command: the original user command starting with "share" 
    commands: the processed list that represent the command
    (return value of process_command_into_list function)
    @return:
    check flags, identify different parameters to be passed into different share funcitons
    and call the share functions if the command is verified as valid
    @valid_command_format:
    1, full fomat: share -m 'email message' -r 'role' -e 'emailAddresses separated by spaces'
    -g 'groupEmailAddresses separated by spaces'
    -d 'domainEmailAddresses separated by spaces'
    'file_path' 
    2, command without '-m' flag: No invitation emails will be sent
    3, specify at least one email address/group email address or a domain, i.e. the command
    need to contain at least one of the flag '-e','-g','-d' followed by some contact info (email addresses)
    4, if no email address is provided, the file would be shared with anyone. Type= 'anyone'
    5, '-r' flad define roles of the person to share the file with, can be reader, writer, commenter,
    or even owner. Default role: reader
    6, 'file_path' is mandatory. It specifies the file to be shared
    '''
    if len(ls)<=1:
        print ("Invalid command: "+ command)
        print("Please make sure that you followed the command protocol")
        print ("To share file: share -m 'email message' -r 'r/w/c/o' -e 'emailAddress1 emailAddress2 emailAddress3' -g 'groupEmailAddress' -d 'domainEmailAddess' 'file_path'")
        print ("You must have a file path, other parts can be skipped")
        print ("Please type \"share -h\" or \"share -help\" to better understand the function\"")
        return
    if len(ls)==2 and (ls[1]=='-h' or ls[1]=='-help'):
        print ("To share files with people, the command should follow these rules: ")
        print ("   1, full fomat: share -m 'email message' -r 'role' -e 'emailAddresses separated by spaces'")
        print ("   -g 'groupEmailAddresses separated by spaces'")
        print ("   -d 'domainEmailAddresses separated by spaces'")
        print ("    'file_path' ")
        print ("   2, command without '-m' flag: No invitation emails will be sent")
        print ("    3, specify at least one email address/group email address or a domain, i.e. the command")
        print ("    need to contain at least one of the flag '-e','-g','-d' followed by some contact info (email addresses)")
        print ("    4, if no email address is provided, the file would be shared with anyone. Type= 'anyone'")
        print ("    5, '-r' flad define roles of the person to share the file with, can be reader, writer, commenter,")
        print ("   6, 'file_path' is mandatory. It specifies the file to be shared")
        return
    #file_id
    file_path=ls[-1]
    file_id=findID(file_path)
    if file_id==None:
        return

    #emailMessage
    sendNotificationEmails=False
    message=""
    m_index=[i for i, m in enumerate(ls) if m=="-m"]
    if len(m_index)>=2:
        print ("Invalid command: "+command)
        print ("We can only have write messages through one email")
        return
    if len(m_index)==1:
        sendNotificationEmails=True
        message= ls[m_index[0] +1]

    #role
    r_index=[i for i, t in enumerate(ls) if t=="-r"]
    if len (r_index)>=2:
        print ("Invalid command: "+command)
        print ("Each share permission can have only one role: o(owner), r(reader), w(writer), c(commenter)")
        return
    if len(r_index)==0:
        role="reader"
    else:
        role=ls[r_index[0]+1]
        assert role in ['o','owner','r','reader','w','writer','c','commenter']

    #type
    no_type=True
    e_index=[i for i, t in enumerate(ls) if t=="-e"]
    if len (e_index)>=2:
        print ("Invalid command: "+ command)
        print ("You can share files with many people by typing: \"share -e 'emailPerson1 emailPerson2 [...]' [...]'file_path'\"")
        print ("Only one '-e' flag is allowed")
        return
    elif len (e_index)==1:
        per_type="user"
        no_type=False
        values=ls[e_index[0]+1].split()
        if sendNotificationEmails==True:
            for value in values:
                insert_share_notif(service,file_id,message,role,per_type,value)
        else:
            for value in values:
                insert_share(service,file_id,role,per_type,value)

    g_index=[i for i, g in enumerate(ls) if g=="-g"]
    if len (g_index)>=2:
        print ("Invalid command: "+command)
        print("You can share files with one or many groups by typing: \"share -g 'groupEmail1 groupEmail2 [...]' [...] 'file_path'\"")
        print ("Only one '-g' flag is allowed")
        return
    elif len (g_index)==1:
        no_type=False
        per_type="group"
        values=ls[t_index[0]+1].split()
        if sendNotificationsEmails==True:
            for value in values:
                insert_share_notif(sevice,file_id,message,role,per_type,value)
        else:
            for value in values:
                insert_share(service,file_id,role,per_type,value)

    d_index=[i for i, d in enumerate(ls) if d=="-d"]
    if len (d_index)>=2:
        print ("Invalid command: "+command)
        print("You can share files with one or many domains by typing: \"share -d 'domain1 domain2 [...]' [...] 'file_path'\"")
        print ("Only one '-d' flag is allowed")
        return
    elif len (d_index)==1:
        no_type=False
        per_type="domain"
        values=ls[d_index[0]+1].split()
        if sendNotificationsEmails==True:
            for value in values:
                insert_share_notif(sevice,file_id,message,role,per_type,value)
        else:
            for value in values:
                insert_share(service,file_id,role,per_type,value)

    if no_type:
        per_type="anyone"
        value=""
        if sendNotificationsEmails==True:
            insert_share_notif(service,file_id,message,role,per_type,value)
        else:
            insert_share(service,file_id,role,per_type,value)
    return None


def process_command_into_list(command):
    '''
    @param: user's command
    @return: a list of different components of user's command
    Ex: "ls -r 'folder_path'"--> ['ls', '-r', 'folder_path']
            "copy -n 'file_name' 'original_file_path'       'copy_file_path'"
            -->['copy','-n','file_name','original_file_path','copy_file_path']
    '''
    result=[]
    last_index=len(command)-1
    start_quote=False
    space_before=True
    i=0
    while i<len(command):
        #print (command[i])
        if command[i] !="'" and (not command[i].isspace()):
            start_index=i
            end_index=command.find(" ",i)
            #print ("Case 1: "+str(end_index))
            if end_index==-1:
                end_index=len(command)
            word=command[start_index : end_index]
            result.append(word)
            i=end_index+1
            continue
        if command[i]=="'":
            start_index=i+1
            end_index=command.find("'",start_index)
            #print ("Case 2: "+ str(end_index))
            if end_index==-1:
                end_index=len(command)
            result.append(command[start_index : end_index])
            i=end_index+1
            continue
        else:
            i+=1
    return result
        
def process_command(service, command):
    '''
    @param: service
                    command: user's command
    @return: process user's command and decide which function to call to execute user's command
    '''
    ls=process_command_into_list(command)
    if ls[0]=='ls' or ls[0]=='list':
        process_list(service,command,ls)
        return
    if ls[0]=="upload":
        process_upload(service,command,ls)
        return
    if ls[0]=="download":
        process_download(service,command,ls)
        return
    if ls[0]=="copy":
        process_copy(service,command,ls)
        return
    if ls[0]=="delete":
        process_delete(service,command,ls)
        return
    if ls[0]=="share":
        process_share(service,command,ls)
    if ls[0]=="quit" or ls[0]=="q":
        print ("Quitting DriveShell ....")
        os._exit(0)
    else:
        print ("Invalid command: "+command)
        print("supported commands: ls, upload, download, copy, delete")
        return

def process_multiple_commands(command):
    '''
    Users can sequentially multiple commands in one singe command using '|' as delimiter
    This function simply return a list of such commands 
    '''
    return command.split("|")

def print_id_name_parents():
    '''
    print the id_name_parents dictionary for testing purposes
    '''
    for thing in id_name_parents:
        print(id_name_parents[thing].getName()+"  "+ thing)

def print_name_id():
    '''
    print the name_id dictionary for testing purposes
    '''
    for thing in name_id:
        print (thing+ "   "+str(name_id[thing]))

def main():
    credentials=get_credentials()
    http=credentials.authorize(httplib2.Http())
    service=discovery.build('drive','v2',http=http)
    initialize_dictionaries(service)
    while True:
        commands=raw_input("prompt>>>  ")
        commands=process_multiple_commands(commands)
        for command in commands:
            process_command(service,command)
        
main()
