# Coronavirus Cases Analysis

Analysis related to the current outbreak of coronavirus disease (COVID-19). It was first reported from Wuhan, China, on 31 December 2019 and it was declared a Public Health Emergency of International Concern on 30 January 2020.

## Introduction

Let's try to get some numbers and analyze what is going on:
 - gather data from [WHO](https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports/)
   - get daily situation report
   - parse pdf content in order to extract data from pdf report
 - Compute statistics
 - Visual analysis by plotting data using charts and maps
   - Distribution of COVID-19 cases worldwide and for each country
   - Epidemiological curve worldwide and for each country

There is a main program to get the data and a jupyter-notebook to analyze it

## Main program

Take the data from web site of [World Health Organization](https://www.who.int/).
They published different situation report daily, there is a page with the links to each situation report that is a pdf file.
Extract the data from the pdf file considering that there are different kind of structures they used.
You can execute the program many times and it saves intermediary results in order to performe computations only for data of new situation reports.

## Jupyter-notebook

Load the dataframe with csv data.
Clean the data, convert types and format in order to use proper values.
Get the "countries" with the maximum number of cases.
Visualize the graphps of the cases in the countries day by day.
Compare epidemiological curves of the countries.

