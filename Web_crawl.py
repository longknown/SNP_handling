#!/usr/bin/python

import os
import sys
import re
import requests as req
import bs4

def capture_gene(line):
    '''this function is defined to capture the genes out of the html lines'''
    sp = bs4.BeautifulSoup(str(line))
    return sp.find('a').string

gene = str(sys.argv[1])
baseurl = 'http://ricevarmap.ncpgr.cn/'
genelist_url = baseurl + 'snp_in_gene/?'

# Following block is the retrieve of gene_list according to gene names or symbols
user_agent = {'User-agent': 'chrome'} # to be masked as a chrome browser
payload = {'gene_func': gene}
genelist_r = req.get(genelist_url, params=payload, headers=user_agent)

# to handle the retrieved web-page using bs4
soup = bs4.BeautifulSoup(genelist_r.text)

# check whether there's resulting MSU genes for the input gene names
if soup.find('h2').next_sibling.next_sibling.name == 'div':  # the resulting web site shows when there's no resulting genes, the next to the next sibling of h2 would be 'div' other than 'p'
    print "Sorry, we can't find any gene function or gene symbol matching the keyword."
    os._exit(0)
elif not soup.find(attrs={'class': 'current page'}).parent.find_all('a'):  #the following 2 options are for distinguish whether multiple pages are returned,
    genelist = soup.find('table',attrs={'class': re.compile('table-striped')}).find_all('a')
else:
    page_number = len(soup.find(attrs={'class': 'current page'}).parent.find_all('a'))  # obtain the number of web page numbers
    genelist = []
    for i in range(1, page_number+1):  # Recursively handle each web page
        genelist_url = baseurl + 'snp_in_gene/?'
        payload['page'] = str(i)
        genelist_r = req.get(genelist_url, params=payload, headers=user_agent)
        soup = bs4.BeautifulSoup(genelist_r.text)
        add_gene = soup.find('table',attrs={'class': re.compile('table-striped')}).find_all('a')
        genelist.extend(add_gene)

loc_list = [capture_gene(line) for line in genelist]  # to handle the html-hidden gene locus for further gene mining
