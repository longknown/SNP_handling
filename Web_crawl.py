#!/usr/bin/python

import os
import sys
import re
import requests as req
import bs4
import Image
from StringIO import StringIO



def capture_gene(line):
    '''Short function defined to capture the genes out of the html lines'''
    sp = bs4.BeautifulSoup(str(line))
    return str(sp.find('a').string)  # to ensure the returned value is of string type


def find_gene_loc(gene, genelist_url, user_agent):
    '''Step1 function:

    Description: for a given gene symbol, crawl the web to capture the locus names of the gene symbol;
    Usage:
        find_gene_loc(gene, genelist_url, user_agent)
        main parameter is gene(gene symbol, e.g. FLC); other parameters are passed on from the main program
    '''

    payload = {'gene_func': gene}
    try:
        genelist_r = req.get(genelist_url, params=payload, headers=user_agent)
    except Exception as e:
        print('Network Exception:', e)


    # to handle the retrieved web-page using bs4
    soup = bs4.BeautifulSoup(genelist_r.text)

    # check whether there's resulting MSU genes for the input gene names
    if not soup.find('table', attrs={'class': re.compile('table-striped')}):
        print "Sorry, we can't find any gene function or gene symbol matching the keyword.\n"
        os._exit(0)
    elif not soup.find(attrs={'class': 'current page'}).parent.find_all('a'):  #the following 2 options are for distinguish whether multiple pages are returned,
        genelist = soup.find('table', attrs={'class': re.compile('table-striped')}).find_all('a')
    else:
        page_number = len(soup.find(attrs={'class': 'current page'}).parent.find_all('a'))  # obtain the number of web page numbers
        genelist = []
        for i in range(1, page_number+1):  # Recursively handle each web page
            genelist_url = baseurl + 'snp_in_gene/?'
            payload['page'] = str(i)
            try:
                genelist_r = req.get(genelist_url, params=payload, headers=user_agent)
            except Exception as e:
                print('Network Exception:', e)
            soup = bs4.BeautifulSoup(genelist_r.text)
            add_gene = soup.find('table', attrs={'class': re.compile('table-striped')}).find_all('a')
            genelist.extend(add_gene)

    loc_list = [capture_gene(line) for line in genelist]  # to handle the html-hidden gene locus for further gene mining
    return loc_list


def capture_snp(line):
    '''similar to capture_gene'''

    soup = bs4.BeautifulSoup(str(line))
    snp = str(soup.td.text)[:-5]
    return snp


def get_special_snp(loc_soup):
    '''build to capture special SNPs

    for each passed web-page, capture the corresponding special SNPs including NS SNP & initial/stop codon
    '''

    special_snp = []
    if not loc_soup.find('table', attrs={'class': 'itable'}):  # in case of those locus without any SNPs
        return special_snp
    else:
        ns_symbol = 'text\-(info|danger)'  # text-info & text-danger are the symbols for special SNPs
        snp = loc_soup.find('table', attrs={'class': 'itable'}).find_all('tr', attrs={'class': re.compile(ns_symbol)})
        if snp:
            special_snp = [capture_snp(line) for line in snp]

        return special_snp


def capture_percent(perc):
    '''the same type as capture_*
    but the returned value is a float number, which represents the number of percentage.
    '''

    p_soup = bs4.BeautifulSoup(str(perc))
    percentage = float(p_soup.td.next_sibling.next_sibling.string[1:-2])  # the text value in the table is u'\rXX% '
    return percentage


def test_snp(snp):
    '''to test whether a snp is dictinct between indica & japonica
    the cut-off distinction is 40% (percentage: |indica - japonica| >= 40%)
    return value is a boolen, True for distinct, False for non-distinct
    '''

    snp_url = 'http://ricevarmap.ncpgr.cn/snp/?'
    payload = {'snp_id': snp}
    user_agent = {'User-agent': 'chrome'} # to be masked as a chrome browser
    try:
        page = req.get(snp_url, params=payload, headers=user_agent)
    except Exception as e:
        print('Network Exception:', e)
    page_soup = bs4.BeautifulSoup(page.text)
    cut_off = 40

    distinct = False

    percent = page_soup.find('table', attrs={'class': 'imagetable'}).tbody.find_all('tr')
    indica = capture_percent(percent[1])
    japonica = capture_percent(percent[2])
    if abs(indica-japonica) >= cut_off:
        distinct = True
    return distinct


def get_table(loc_soup, special_snp, distinct_snp):
    '''From the web-page, capture the table out, with special notes for distinct & biological important meanings
    '''

    table_content = ''
    origin_list = loc_soup.find('table', attrs={'class': 'itable'}).find_all('tr')
    th_soup = bs4.BeautifulSoup(str(origin_list[0]))  # special handling for the table head(th)
    th_n = str(th_soup.text) + 'Special or NOT\nDistinct or NOT'
    th = th_n[1:].replace('\n', '\t')
    table_content += th + '\n'

    for item in origin_list[1:]:
        item_soup = bs4.BeautifulSoup(str(item))
        tr_n = str(item_soup.text)
        tr = tr_n[1:].replace('\n', '\t').replace('\r', '')
        snp = tr_n.split()[0][:-5]

        print special_snp
        print snp
        if snp in special_snp:
            tr += '\t*'
        else:
            tr += '\t '
        if snp in distinct_snp:
            tr += '\t*'
        else:
            tr += '\t '
        table_content += tr + '\n'

    return table_content





### Main Program ###
gene = str(sys.argv[1]).upper()
baseurl = 'http://ricevarmap.ncpgr.cn/'
genelist_url = baseurl + 'snp_in_gene/?'

# Following block is the retrieve of gene_list according to gene names or symbols
user_agent = {'User-agent': 'chrome'}  # to be masked as a chrome browser

# Step1: Find out the numerous gene locus
loc_list = []
loc_list = find_gene_loc(gene, genelist_url, user_agent)

gene_dir = '../' + gene  # to create a new directory for each gene, path: ../gene
exist_path = os.path.exists(gene_dir)
if not exist_path:
    os.mkdir(gene_dir)


# Step2: Screen the Non-Synonymous SNPs
distinct_loc = []  # to store those loc_name with distinct special SNPs
csv_content = ''  # to store an integrated table with TAB
for loc in loc_list:
    payload = {'gene_ids': loc}
    try:
        loc_r = req.get(genelist_url, params=payload, headers=user_agent)
    except Exception as e:
        print('Network Exception:', e)
    loc_soup = bs4.BeautifulSoup(loc_r.text)
    special_snp = get_special_snp(loc_soup)
    distinct_snp = filter(test_snp, special_snp)  # Step3:\
    #  Screen out SNPs with distinct distribution between indica & japonica

    if distinct_snp:
        # Store the image first
        img_url = str(loc_soup.img.attrs['src'])  # the SNP distribution image url
        try:
            img_r = req.get(img_url, headers=user_agent)
        except Exception as e:
            print('Network Exception:', e)
        img_path = gene_dir + '/' + loc + '.png'
        img = Image.open(StringIO(img_r.content))
        img.save(img_path)

        distinct_loc.append(loc)
        csv_content = csv_content + loc + '\n'

        print distinct_snp
        table_content = get_table(loc_soup, special_snp, distinct_snp)
        csv_content += table_content
csv_path = gene_dir + '/' + gene + '.csv'
loc_csv_path = gene_dir + '/' + 'loc.csv'

# Write the table to local disk
with open(csv_path, 'wt') as f1:
    f1.write(csv_content)
    f1.close()
with open(loc_csv_path, 'wt') as f2:
    for snp in distinct_loc:
        f2.write('\n')
        f2.write(snp)
    f2.close()
