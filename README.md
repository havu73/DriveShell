# DriveShell
DriveShell is a personal winter break project that I implemented  to practice reading APIs and coding in general.
DriveShell acts as a terminal for Google Drive. With DriveShell and internet connections, you can type in commands in 
your local terminal to manage files in the cloud. 
Some functions that this program supports include list files (recursively or not), uploading and downloading files, 
copying and deleting files, sharing files (with invitation emails or not). I will add a new function to unshare files very soon.

# Set up
To use DriveShell, you need:

1, Client library for Google Drive in Python. 
```
pip install --upgrade google-api-python-client
```

2, httplib2 in Python
```
pip install httplib2
```

If you have multiple versions of Python, please make sure that you install httplib2 in the right version. 
Check out this [forum thread](http://stackoverflow.com/questions/17116290/importerror-no-module-named-httplib2-but-httplib2-is-installed)
if you encounter some problems.

3, A client_secret file of your Google account. Please read Step 1 in the following [page](https://developers.google.com/drive/v3/web/quickstart/python) 
to get your client_secret.json file. Put the file 'client_secrets.json' into the local directory where DriveShell.py resides.
If you have multiple Google Accounts and wants to manage files in multiple Google Drive-s, please be patient, I will
add some code to allow you to choose which account you want to managefiles with very soon.

# Commands
##Some rules in file paths
1, Specify full Google Drive file path. Examples: 
```
My Drive/Folder1
My Drive
My Drive/Folder2/Folder3/File4.extension
```
2, Specify local file path relative to the Home directory. Examples:
```
Desktop/file1.extension
Downloads/DownloadSubFolder/DownloadFile.extension
```
## List files:
To list only files in Google Drive directory:
```
ls 'My Drive/Folder1/Folder2'
```
or 
```
list 'My Drive/Folder1/Folder2'
```
Example output:
```
upload.png   0Bx2aTklRTnmiOHVER2ttWkZYSms
Folder1   0Bx2aTklRTnmiVFBIcW5IWllrSmM
File1   1rJ2owbwrhDLNeNihyxJhWyRio11CzHtJ6J5NRYRe1Ng
```
The string follows each file/directory is file ID.

To recursively list files in a Google Drive directory:
```
ls -r 'My Drive'
```
or 
```
list -r 'My Drive'
```

Example output:
```
upload.png   0Bx2aTklRTnmiOHVER2ttWkZYSms
Folder1   0Bx2aTklRTnmiVFBIcW5IWllrSmM
     File2.png   0Bx2aTklRTnmiS1BEN0dVYlRILUU
     folder2   0Bx2aTklRTnmiRWVQRGJMTmxuZHc
          Copy of File1   1KCamI1hPna_5X3Okmm4JEXmeFlFBzRTP2cnRAlUtmnI
          file3.png   0Bx2aTklRTnmicmM3bndOVjZ0RnM
File1   1rJ2owbwrhDLNeNihyxJhWyRio11CzHtJ6J5NRYRe1Ng
```

##Delete files:
To delete a file: 
```
delete 'My Drive/Folder1/deleteFile.extension'
```
##Copy files:
To copy into a new folder with a name specified by user:
```
copy -n 'newFileName.extension' 'My Drive/Folder/copyfile.extension' 'My Drive/.../DestinationFolder'
```
If the ```-n 'newFileName.extension'`` flag is not added, the new file name would be ```Copy of ``` +original file name. Example:
```
copy 'My Drive/copyfile.extenstion' 'My Drive/.../DestinationFolder'
```
would result in a file named ```Copy Of copyfile.extension``` in ```DestinationFolder```

If the Destination Folder is not specified, then default value would be the directory where the original file resides. In this case, 
if the new file name is the same as the old file name, the program would not accept the command and hence not execute the copy
command.

## To be continued...
