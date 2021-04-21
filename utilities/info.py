import inspect
import importlib
import ast
import os

EXCEPTIONS = ['.testervenv', '.git', '__pycache__']

# def get_files(dirName):
#     # create a list of file and sub directories 
#     # names in the given directory 
#     listOfFile = os.listdir(dirName)
#     allFiles = list()
#     # Iterate over all the entries
#     for entry in listOfFile:
#         # Create full path
#         fullPath = os.path.join(dirName, entry)
#         # If entry is a directory then get the list of files in this directory 
#         if os.path.isdir(fullPath):
#             if '.testervenv' in fullPath or '__pycache__' in fullPath:
#                 continue
#             allFiles = allFiles + get_files(fullPath)
#         else:
#             if not fullPath.endswith(".py"):
#                 continue
#             allFiles.append(fullPath)      
        
#     print(allFiles)
#     return allFiles
mod = importlib.import_module('./cogs.manager.py')

#fobj = inspect.getmodulename('./core.py')
#print(fobj)