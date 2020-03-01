import requests
import re
import json
import pandas
import os
from os import listdir
from os.path import isfile, join
import datetime
from bs4 import BeautifulSoup # for parsing html and extracting situation reportr urls
import PyPDF2 # for extracting data from pdf
import re


# make http request to given url and save response to file
def downloadContent(url, fileName):
    try:
        x = requests.get(url)
        with open(fileName, 'wb') as f:
            f.write(x.content)
        obj={
            'url': url
        }
        with open(fileName+".meta", 'w+', encoding="utf-8") as f:
            f.write(json.dumps(obj))
        return x
    except Exception as e:
        print('error '+fileName)
        print(e)

# save all responses of given requests in specified basePath
def saveResponses(basePath, requests):
    for r in requests:
        downloadContent(r['url'], os.path.join(basePath , r['name']))

''' # return an url that is the same as baseUrl with replacement specified in the dictionary
def getUrl(baseUrl, replacement):
    url = baseUrl
    for k in replacement:
        url = url.replace(k, replacement[k])
    return url

# get requests data for report between given dates
def getCovidReportRequests(baseUrl, minDate, maxDate):
    requests = []
    date=minDate
    i=1
    while date <= maxDate:
        url = getUrl(baseUrl, {
            'DATE': date.strftime('%Y%m%d'),
            'SEQUENCE': str(i)
        })
        requests.append({
            'url': url,
            'name': 'report'+date.strftime('%Y-%m-%d')
        })
        i = i+1
        date = date + datetime.timedelta(days=1)
    return requests '''

# download page with links to each situation report (there are daily situation reports)
def downloadReportsList(path):
    # download main page with urls to all situation reports
    url = 'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports'
    downloadContent(url, path)

# extract from the page with situation reports list the url for each one
# return a list with dictionary, each dict has url and name attributes
def getReportUrls(reportsListPath):
    baseUrl = 'https://www.who.int'
    result = []
    with open(reportsListPath, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        elements = soup.select('.sf-content-block.content-block p')
        for el in elements:
            try:
                url = el.select_one('a')
                if(url is not None):
                    url = baseUrl + url['href']
                    name = el.text.replace(u'\xa0', u' ')
                    result.append({
                        'url':url,
                        'name': name
                    })
            except Exception as e:
                print('Exception during parsing of an element expected to have an url')
                print(e)
    return result

# download all situation reports
def downloadReports(basePath, reportListPath):
    downloadReportsList(reportListPath)
    requests = getReportUrls(reportListPath)
    saveResponses(basePath, requests)

# extract text from pdf file
# return a list with a string for each page of the pdf file
def extractTextFromPdf(path):
    result = []
    with open(path, 'rb') as f:
        pdfReader = PyPDF2.PdfFileReader(f)
        i = 0
        while i < pdfReader.numPages:
            pageObj = pdfReader.getPage(i)
            text = pageObj.extractText()
            result.append(text)
            i = i+1
    return result

# extract text of the data table from content string
def extractTableTextFromReport(content):
    startDataTitle = 'SURVEILLANCE\n'
    endDataTitle = 'PREPAREDNESS AND RESPONSE'
    text = ''
    if startDataTitle in content:
        text = content[content.index(startDataTitle) + len(startDataTitle):]
        if endDataTitle in text:
            text = text[:text.index(endDataTitle)]
    else:
        print('no data found, missing '+startDataTitle+' string in '+path)
    return text
    

# extract data table from text
# in the text there are many objects: each one has a name and some numbers after it (values)
# the interesting objects are those with one or more values attached
def extractDataFromText(text, skipRegex):
    result = []
    lines = text.split('\n')
    structureWithPopulation = '10,000s' in text
    structureWithDailyNumbers = 'Daily\n' in text
    n_table = 0
    obj = {
        'name': '',
        'values':[],
        'structureWithPopulation':structureWithPopulation,
        'structureWithDailyNumbers':structureWithDailyNumbers,
        'n_table':n_table
    }
    for line in lines:
        line = line.strip()
        if 'Table' in line:
            n_table = n_table + 1
        if line != '' and re.match(skipRegex, line) is None: # skip empty lines and lines that match the skipRegex
            match = re.match(r'\d+|-',line) # check if it is a number
            if match:
                val = match.group()
                if val == '-':
                    val = 0
                else:
                    val = int(val)
                obj['values'].append(val) # add value to current object
            else:
                if len(obj['values']) > 0: # do not consider object without values
                    result.append(obj)
                obj = {
                    'name': line,
                    'values':[],
                    'structureWithPopulation':structureWithPopulation,
                    'structureWithDailyNumbers':structureWithDailyNumbers,
                    'n_table':n_table
                }      
    return result


if __name__ == '__main__':
    basePath = 'data'
    path = os.path.join(basePath,'reportsList.html')
    downloadReportsList(path)
    l=[]
    reportList = getReportUrls(path)
    for r in reportList:
        print(r['name'])
        # make request and save response (the response is a pdf file with the situation report) if it does not exist
        response_path = os.path.join(basePath,r['name'])
        if not os.path.exists(response_path):
            print('\tMake request')
            saveResponses(basePath, [r])
        # extract text from pdf and save text file if it does not exist
        dest_path = os.path.join(basePath,r['name']+'.txt')
        if not os.path.exists(dest_path):
            print('\tConvert pdf to text')
            pages = extractTextFromPdf(response_path)
            text = '\n'.join(pages)
            # save pdf content as text file
            with open(dest_path, 'w+',encoding='utf-8') as f:
                f.write(text)
        else:
            with open(dest_path,'r',encoding='utf-8') as f:
                text = f.read()
        # extract table data
        dataPath = os.path.join(basePath,r['name']+'.csv')
        if True or not os.path.exists(dataPath):
            print('\tExtract data table')
            t=extractTableTextFromReport(text)
            data=extractDataFromText(t,'Imported cases only|Local transmission')
            df = pandas.DataFrame(data)
            df.to_csv(dataPath)
        else:
            df = pandas.read_csv(dataPath)
        df['report']=r['name']
        l.append(df)
    d = pandas.concat(l)
    d.to_csv(os.path.join(basePath,'df'+datetime.date.today().isoformat()+'.csv'))
    print('launch jupyter notebook')
    