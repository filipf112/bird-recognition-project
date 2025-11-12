#!/usr/bin/env/python

# A script to download bird sound files from the www.xeno-canto.org archives with metadata

import urllib.request, json, urllib.parse
import sys
import os
import ssl
import shutil 

# ===================================================================
# == API KEY ==
# ===================================================================
API_KEY = "1e6a9aa9802ece76fb29a052bab47076c3c2afdd"
# ===================================================================


# http://www.xeno-canto.org/explore?query=common+snipe
ssl._create_default_https_context = ssl._create_unverified_context

# Creates the subdirectory data/xeno-canto-dataset if necessary
# Downloads and saves json files for number of pages in a query
# and directory path to saved json's
def save_json(searchTerms):
    numPages = 1
    page = 1
    #create a path to save json files and recordings
    path = "data/" + ''.join(searchTerms).replace(':', '_').replace('"', '')
    if not os.path.exists(path):
        print("Creating subdirectory " + path + " for downloaded files...")
        os.makedirs(path)
        
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("Error: API_KEY is not set. Please get a key from xeno-canto.org and add it to the script.")
        sys.exit(1) 
        
    #download a json file for every page found in a query
    while page < numPages + 1:
        print("Loading page " + str(page) + "...")
        
        # 1. Join all search terms with a space
        query_string = ' '.join(searchTerms) 
        
        # 2. URL-encode the complete query string
        encoded_query = urllib.parse.quote(query_string)
        
        # 3. Format the final URL
        url = 'https://www.xeno-canto.org/api/3/recordings?query={0}&page={1}&key={2}'.format(encoded_query, page, API_KEY)
        print(url)

        try:
            with urllib.request.urlopen(url) as jsonPage:
                jsondata = json.loads(jsonPage.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code} {e.reason}")
            if e.code == 400:
                 print("Error: Bad Request. Your query is likely malformed.")
                 print("Remember, API v3 requires tags (e.g., 'sp:\"Apus apus\"' or 'gen:Apus sp:apus').")
            return None 
        except Exception as e:
            print(f"An error occurred: {e}")
            return None 
            
        filename = path + "/jsondata_p" + str(page) + ".json"
        with open(filename, 'w') as outfile:
            json.dump(jsondata, outfile)
            
        #check number of pages
        numPages = jsondata['numPages']
        page = page + 1
        
    print("Found ", numPages, " pages in total.")
    # return number of files in json
    # each page contains 500 results, the last page can have less than 500 records
    print("Saved json for ", (numPages - 1) * 500 + len(jsondata['recordings']), " files")
    return path

# reads the json and return the list of values for selected json part
def read_data(searchTerm, path):
    data = []
    numPages = 1
    page = 1
    #read all pages and save results in a list
    while page < numPages + 1:
        # read file
        try:
            with open(path + "/jsondata_p" + str(page) + ".json", 'r') as jsonfile:
                jsondata = jsonfile.read()
        except FileNotFoundError:
            print(f"Error: Could not find JSON file for page {page}. Stopping.")
            break
            
        jsondata = json.loads(jsondata)
        # check number of pages
        numPages = jsondata['numPages']
        # find "recordings" in a json and save a list with a search term
        for k in range(len(jsondata['recordings'])):
            if searchTerm in jsondata["recordings"][k]:
                data.append(jsondata["recordings"][k][searchTerm])
            else:
                print(f"Warning: '{searchTerm}' not found in record {k} on page {page}")
        page = page + 1
    return data


# downloads all sound files found with the search terms into xeno-canto directory
def download(searchTerms):
    # create data/xeno-canto-dataset directory
    path = save_json(searchTerms)
    
    # Check if save_json failed (e.g., due to auth error)
    if path is None:
        print("Failed to retrieve JSON data. Halting download.")
        return
        
    # get filenames: recording ID and bird name in latin from json
    filenamesID = read_data('id', path)
    filenamesGen = read_data('gen', path)
    # get website recording http download address from json
    fileaddress = read_data('file', path)
    numfiles = len(filenamesID)
    
    if numfiles == 0:
        print("No files found to download.")
        return

    print("A total of ", numfiles, " files will be downloaded")
    for i in range(0, numfiles):
        print("Saving file ", i + 1, "/", numfiles, ": " + filenamesGen[i] + filenamesID[i] + ".mp3")
        
        # 1. Get the URL. It might be protocol-relative (starts with //)
        url = fileaddress[i]
        if url.startswith('//'):
            url = 'https:"' + url # Add "https:" to make it a full URL
            
        # 2. Define the local save path
        save_path = path + "/" + filenamesGen[i].replace(':', '') + filenamesID[i] + ".mp3"

        # 3. Create the request, but without the Auth header
        try:
            req = urllib.request.Request(url)
            # Add a User-Agent, as some servers require it
            req.add_header('User-Agent', 'MyXenoCantoDownloader/1.0') 

            # 4. Open the URL and save the file
            with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
        except Exception as e:
            print(f"  -> FAILED to download {url}. Error: {e}")


def main(argv):
    if (len(sys.argv) < 2):
        print("Usage: python xcdl.py searchTerm1 searchTerm2 ... searchTermN")
        # Updated example to show correct API v3 usage
        print("Example (species): python xcdl.py sp:\"Apus apus\"")
        print("Example (genus+species): python xcdl.py gen:Apus sp:apus")
        print("Example (quality): python xcdl.py sp:\"Apus apus\" q:A")
        return
    else:
        download(argv[1:len(argv)])


if __name__ == "__main__":
    main(sys.argv)