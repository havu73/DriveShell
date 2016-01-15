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
    """Given a path(string),
    find the id of the file referenced by the  path
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
    children=service.files().list(q="'%s' in parents and trashed=false"%fID
                                     ,spaces="drive"
                                     ,fields="items(title,id)").execute()
    
    for child in children['items']:
        print (child['title']+"   "+child['id'])

def list_file_alt(service,fID):
    children=service.children().list(folderId=fID,fields="items(id)").execute()
    for child in children['items']:
        print((child["id"]))
        fileRef=id_name_parents[child['id']]
        print (fileRef.getName()+"     "+fileRef.getID())
        
def list_file_recursive(service,fID,space):
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
        
def add_id_name_parents(fileID,name,parent):#parent should be just a single string
    if not (fileID in id_name_parents):
        id_name_parents[fileID]=idR(fileID,name,[parent])
    else:
        id_name_parents[fileID].add_parent(parent)

def add_name_id(fileID,name):#fildID is a string
    if not (name in name_id):
        name_id[name]=[fileID]
    else:
        name_id[name].append(fileID)
        
def upload(service,file_path,folder_id,file_name):
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
    del(id_name_parents[file_id])

def delete_name_id(name):
    del(name_id[name])
    
def delete(service,delete_id):
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
    if len(ls)<=1:
        print ("Invalid command: "+ command)
        print("Please make sure that you followed the command protocol")
        print ("To share file: share -m 'email message' -t 'r/w/c' -e 'emailAddress1 emailAddress2 emailAddress3' -g 'groupEmailAddress' -d 'domainEmailAddess' 'file_path'")
        print ("You must have a file path, other parts can be skipped")
        print ("Please type \"share -h\" or \"share -help\" to better understand the function\"")
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
        print ("Each share permission can have only one role: r(reader), w(writer), c(commenter)")
        return
    if len(r_index)==0:
        role="reader"
    else:
        role=ls[r_index[0]+1]
        assert role in ['r','reader','w','writer','c','commenter']

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
        
def process_command(service, command):#process one single command
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
    else:
        print ("Invalid command: "+command)
        print("supported commands: ls, upload, download, copy, delete")
        return
    
def print_id_name_parents():
    for thing in id_name_parents:
        print(id_name_parents[thing].getName()+"  "+ thing)

def print_name_id():
    for thing in name_id:
        print (thing+ "   "+str(name_id[thing]))

def main():
    credentials=get_credentials()
    http=credentials.authorize(httplib2.Http())
    service=discovery.build('drive','v2',http=http)
    initialize_dictionaries(service)
##    fileID1=findID("My Drive")
    #print (fileID1)
##    for thing in id_name_parents:
##        print (thing+ "     "+ id_name_parents[thing].to_string())
##    

 #   fileID2=findID("My Drive/Folder1/file3")
 #   fileID3=findID("Folder1/folder2")
    
##    list_file(service,fileID2)
##    print("")
##    list_file(service,fileID3)
##    print("")
##    list_file_recursive(service,fileID2)
##    print("")
 #   list_file_recursive(service,fileID1,0)
 #   list_file_recursive(service,fileID1,0)
 #   download(service, "download.png","0Bx2aTklRTnmicmM3bndOVjZ0RnM","/Users/VuThaiHa/Downloads")
 #   upload(service,"/Users/VuThaiHa/Downloads/animBanner.py","root",'upload.py')
 #   copy(service,"0Bx2aTklRTnmicmM3bndOVjZ0RnM","root","copy.png")
 #   list_file_recursive(service,"root",0)
 #   delete(service,"0Bx2aTklRTnmiOE5YYVpuTmNpRXM")
 #   list_file_recursive(service,"root",0)
##    command1="ls -s"
##    list1=process_command_into_list(command1)
##    command2="ls -r 'My Drive/Folder1'"
##    list2=process_command_into_list(command2)
##    command3= "ls 'My Drive'"
##    list3=process_command_into_list(command3)
##    command4="ls 'Folder1/folder2'"
##    list4=process_command_into_list(command4)
##    print("Test1: ")
##    process_list(service,command1,list1)
##    print("Test2: ")
##    process_list(service,command2,list2)
##    print("Test3: ")
##    process_list(service,command3,list3)
##    print("Test4: ")
##    process_list(service,command4,list4)
##
##    command1="upload -n 'upload.png' 'Desktop/upload.png' 'My Drive/Folder1'"
##    print ("Test1:")
##    ls1=process_command_into_list(command1)
##    print (ls1)
##    process_upload(service,command1,ls1)
##    print ("Test2: ")
##    command2="upload -t 'hello.py' 'Desktop/VuThaiHa' 'My Drive/Folder2'"
##    ls2=process_command_into_list(command2)
##    print (ls2)
##    process_upload(service,command2,ls2)
##    print("Test3: ")
##    cm3="upload 'Desktop/upload.png' 'My Drive/Folder1/folder2'"
##    ls3=process_command_into_list(cm3)
##    print (ls3)
##    process_upload(service,cm3,ls3)
##    print("Test4: ")
##    cm4="upload -n 'shouldfail.py' 'Downloads/AnhVien..png' 'My Drive/File1'"
##    ls4=process_command_into_list(cm4)
##    print (ls4)
##    process_upload(service,cm4,ls4)
##    print (findID("My Drive/Folder1/upload.png"))
##    print (findID("My Drive/Folder1/folder2/upload.png"))
##    cm1="ls -r 'My Drive/Folder1'"
##    print (process_command_into_list(cm1))
##    cm2="download -n 'download.py' 'My Drive/Folder1/folder2' 'Downloads'"
##    print (process_command_into_list(cm2))

##    cm1="download -n 'download.doc' 'My Drive/File1' "
##    ls1=process_command_into_list(cm1)
##    print("Test1: file download.png in Downloads")
##    process_download(service,cm1,ls1)
##    cm2="download 'My Drive/upload.png'"
##    ls2=process_command_into_list(cm2)
##    print ("Test2: file upload.png in Downloads")
##    process_download(service,cm2,ls2)
##    cm3="download 'My Drive/Folder1/folder2/file3.png' 'Desktop'"
##    ls3=process_command_into_list(cm3)
##    print("Test3: file file3.png in Desktop")
##    process_download(service,cm3,ls3)
##    cm4="download -n 'hello.py' 'My Drive/Folder1' 'Downloads'"
##    ls4=process_command_into_list(cm4)
##    print ("Test4: Error")
##    process_download(service,cm4,ls4)
##
##    cm1="copy -n 'upload.png' 'My Drive/upload.png' 'My Drive'"
##    ls1=process_command_into_list(cm1)
##    print ("Test1: Should be an error due to file name")
##    process_copy(service,cm1,ls1)
##    cm2="copy 'My Drive/Folder1' 'My Drive/Folder1/folder2'"
##    ls2=process_command_into_list(cm2)
##    print ("Test2: Should be an error due to original file name")
##    process_copy(service,cm2,ls2)
##    cm3="copy 'My Drive/upload.png'"
##    ls3=process_command_into_list(cm3)
##    print ("Test3: Should be ok")
##    process_copy(service,cm3,ls3)
##    cm4="copy 'My Drive/Folder1/file2/file3.png' 'My Drive'"
##    ls4=process_command_into_list(cm4)
##    print ("Test4: ok")
##    process_copy(service,cm4,ls4)
##    print_id_name_parents()
##    print ()
##    print_name_id()
##    cm1="delete 'My Drive/Folder1/deleteFolder'"
##    process_delete(service,cm1,process_command_into_list(cm1))
##    print_id_name_parents()
##    print()
##    print_name_id()
 #   cm2="delete 'My Drive/upload.png'"
 #   process_delete(service,cm2,process_command_into_list(cm2))
    list_file_recursive(service,"root",0)
##    cm="upload 'Desktop/summerOnTheCuyahogaProfile.rtf' 'My Drive'"
##    process_command(service, cm)
    cm="share -m 'share file' -e 'hvu@colgate.edu' 'My Drive/upload.png'"
    process_command(service,cm)
main()
