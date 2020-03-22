import requests
import re
import json
import pandas
import os
from os import listdir
from os.path import isfile, join
import datetime
# for parsing html and extracting situation reportr urls
from bs4 import BeautifulSoup
import PyPDF2  # for extracting data from pdf
import re


def downloadContent(url, fileName):
    """
    make http request to given url and save response to file
    """
    try:
        x = requests.get(url)
        with open(fileName, 'wb') as f:
            f.write(x.content)
        obj = {
            'url': url
        }
        with open(fileName+".meta", 'w+', encoding="utf-8") as f:
            f.write(json.dumps(obj))
        return x
    except Exception as e:
        print('error '+fileName)
        print(e)


def saveResponses(basePath, requests):
    """
    save all responses of given requests in specified basePath
    """
    for r in requests:
        downloadContent(r['url'], os.path.join(basePath, r['name']))


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


def downloadReportsList(path):
    """
    download page with links to each situation report (there are daily situation reports)
    """
    # download main page with urls to all situation reports
    url = 'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports'
    downloadContent(url, path)


def getReportUrls(reportsListPath):
    """
    extract from the page with situation reports list the url for each one
    return a list with dictionary, each dict has url and name attributes
    """
    baseUrl = 'https://www.who.int'
    result = []
    with open(reportsListPath, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        elements = soup.select('.sf-content-block.content-block p')
        # each elemant is a paragraph for a single situation report
        # some paragraphs have more than one 'a' element, only one is the right one
        # save a list of unique urls in order to avoid duplicates
        uniqueUrls = []
        for el in elements:
            try:
                urlEls = el.select('a') # some paragraphs have more than one 'a' element, only one is the right one
                for urlEl in urlEls:
                    url = urlEl['href']
                    if ('sitrep' in url and url not in uniqueUrls): # check if the url is related to the situation report and it is a new one
                        uniqueUrls.append(url)
                        url = baseUrl + url
                        name = el.text.replace(u'\xa0', u' ')
                        result.append({
                            'url': url,
                            'name': name
                        })
            except Exception as e:
                print('Exception during parsing of an element expected to have an url')
                print(e)
    return result


def downloadReports(basePath, reportListPath):
    """
    download all situation reports
    """
    downloadReportsList(reportListPath)
    requests = getReportUrls(reportListPath)
    saveResponses(basePath, requests)


def extractTextFromPdf(path):
    """
    extract text from pdf file
    return a list with a string for each page of the pdf file
    """
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


def extractTableTextFromReport(content):
    """
    extract text of the data table from content string
    """
    startDataTitle = 'ILLANCE\n' # the word should be SURVEILLANCE but in some reports there is only ILLANCE
    endDataTitle = 'PREPAREDNESS AND RESPONSE'
    text = ''
    if startDataTitle in content:
        text = content[content.index(startDataTitle) + len(startDataTitle):]
        if endDataTitle in text:
            text = text[:text.index(endDataTitle)]
    else:
        print('no data found, missing '+startDataTitle+' string in '+path)
    return text


def extractDataFromText(text, skipRegex):
    """
    extract data table from text
    in the text there are many objects: each one has a name and some numbers after it (values)
    the interesting objects are those with one or more values attached
    """
    result = []
    # in the text there are some \n that split the content in a wrong way (for example 1\n4 instead of 14)
    # so replace all '\n' with '' but we need to keep the "right" '\n' and these are easily found because
    # there are sequences of 3 characters '\n \n' that represent the "right" '\n'
    # here an example of raw text:
    """
    \n
    1       # wrong \n
    4
    \n      # start of sequence of '\n \n' of "right" '\n'
     
    \n      # end of sequence of '\n \n' of "right" '\n'
    3
    \n
    """
    replacements = {
        '\n \n': '\n',
        '\n': ''
    }
    regex = re.compile("|".join(map(re.escape, replacements.keys())))
    text = regex.sub(lambda x: replacements[x.group(0)], text) 
    # divide text in lines
    lines = text.split('\n')
    # check some property of the text
    structureWithPopulation = '10,000s' in text
    structureWithDailyNumbers = 'Daily\n' in text or 'In last 24 hours\n' in text
    n_table = 0
    obj = {
        'name': '',
        'values': [],
        'structureWithPopulation': structureWithPopulation,
        'structureWithDailyNumbers': structureWithDailyNumbers,
        'n_table': n_table
    }
    for line in lines:
        line = line.strip()
        if 'Table' in line:
            n_table = n_table + 1
        # skip empty lines and lines that match the skipRegex
        if line != '' and re.match(skipRegex, line) is None:
            # remove empty spaces
            # (sometimes some numbers such as 31211 of China for situation report 2020-02-07 are written '31 211' instead of '31211')
            line = line.replace(' ','')
            match = re.match(r'\d+|-', line)  # check if it is a number or '-' that means 0
            if match:
                val = match.group()
                if val == '-':
                    val = 0
                else:
                    val = int(val)
                obj['values'].append(val)  # add value to current object
            else:
                if len(obj['values']) > 0:  # do not consider object without values
                    result.append(obj)
                obj = {
                    'name': line,
                    'values': [],
                    'structureWithPopulation': structureWithPopulation,
                    'structureWithDailyNumbers': structureWithDailyNumbers,
                    'n_table': n_table
                }
    return result


if __name__ == '__main__':
    basePath = 'data'
    path = os.path.join(basePath, 'reportsList.html')
    downloadReportsList(path)
    l = []
    reportList = getReportUrls(path)
    for r in reportList:
        print(r['name'])
        # make request and save response (the response is a pdf file with the situation report) if it does not exist
        response_path = os.path.join(basePath, r['name'] + '.pdf')
        if not os.path.exists(response_path):
            print('\tMake request')
            downloadContent(r['url'], response_path)
        # extract text from pdf and save text file if it does not exist
        dest_path = os.path.join(basePath, r['name'] + '.txt')
        if not os.path.exists(dest_path):
            print('\tConvert pdf to text')
            pages = extractTextFromPdf(response_path)
            text = '\n'.join(pages)
            # save pdf content as text file
            with open(dest_path, 'w+', encoding='utf-8') as f:
                f.write(text)
        else:
            with open(dest_path, 'r', encoding='utf-8') as f:
                text = f.read()
        # extract table data
        dataPath = os.path.join(basePath, r['name']+'.csv')
        if True or not os.path.exists(dataPath):
            print('\tExtract data table')
            t = extractTableTextFromReport(text)
            data = extractDataFromText(
                t, 'Imported cases only|Local transmission')
            df = pandas.DataFrame(data)
            df.to_csv(dataPath)
        else:
            df = pandas.read_csv(dataPath)
        df['report'] = r['name']
        l.append(df)
    d = pandas.concat(l)
    d.to_csv(os.path.join(basePath, 'df'+datetime.date.today().isoformat()+'.csv'))
    # download italian data of Protezione Civile national service
    downloadContent('https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-regioni/dpc-covid19-ita-regioni.csv', 'data/ITAregioni.csv')
    downloadContent('https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-province/dpc-covid19-ita-province.csv', 'data/ITAprovince.csv')
    print('launch jupyter notebook')
