# coding=UTF-8
# https://github.com/jhnwr/ebay-prices/blob/main/ebayprices.py
# https://www.youtube.com/watch?v=csj1RoLTMIA

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint
from elasticsearch import Elasticsearch

base_url = 'https://www.impcerveceros.com.ar'
product_base_url = 'https://www.impcerveceros.com.ar/shop/product/'

def fetch_page(url):    
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup

def parse_shop_page(soup):
    productslist = []
    results = soup.find_all('td', {'class': 'oe_product'})
    for item in results:
        product = {
            'product_id': item.find('h6', 'o_wsale_products_item_title').find('a')['href'].split('-')[-1].split('?')[0],
            'name': item.find('h6', 'o_wsale_products_item_title').text.replace('\n', ' ').strip(),
            'link': base_url + item.find('h6', 'o_wsale_products_item_title').find('a')['href'].split('?')[0],
            'price': float(item.find('span', 'oe_currency_value').text.replace(',', '')),
            'img_url': base_url + item.find('img', 'img img-fluid')['src'].split('?')[0]
        }

        # fetching stock status
        in_stock_badge = item.find('span', 'badge badge-success position-absolute')
        no_stock_badge = item.find('span', 'badge badge-danger position-absolute')
        if (in_stock_badge is not None and in_stock_badge.text == 'En Stock'):
            product['in_stock'] = 'yes'
        elif (no_stock_badge is not None and no_stock_badge.text == 'Sin Stock'):
            product['in_stock'] = 'no'
        else:
            product['in_stock'] = ''

        productslist.append(product)
    return productslist


# def output(productslist):
#     productsdf =  pd.DataFrame(productslist)
#     productsdf.to_csv('output.csv', encoding='utf-8', index=False)
#     print('Saved to CSV')
#     return

def get_impcervereros_products():
    productslist = []
    page = 1
    
    #while page <= 5: ## TODO change here the value to 19
    while page <= get_last_page_of_shop(): 
        print('Fetching page ' + str(page))
        url = 'https://www.impcerveceros.com.ar/shop/page/' + str(page)
        soup = fetch_page(url)
        productslist += parse_shop_page(soup)
        page += 1

    for product in productslist:
        product_soup = fetch_page(product_base_url + product['product_id'])
        product_description_soup = product_soup.find(id='product_details').find('p', 'text-muted mt-3')
        product['description'] = product_description_soup.text if product_description_soup is not None else ''

        breadcrum = product_soup.find_all('li', 'breadcrumb-item')
        product['primary_category'] = breadcrum[1].text.replace('\n','') if len(breadcrum) > 2 else ''
        product['secondary_category'] = breadcrum[2].text.replace('\n','') if len(breadcrum) > 3 else ''

        # Fetch price from page if it's 0
        if product['price'] == 0:
            product['price'] = float(product_soup.find('div','product_price').find('span', 'oe_currency_value').text.replace(',', '')) 
    return productslist

def get_last_page_of_shop():
    soup = fetch_page(base_url + '/shop/page/500')
    return int(soup.find('li', 'page-item active').text)

def load_on_elasticsearh(products):
    for p in products:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        es.index(index='items',id='imp_' + p['product_id'] , body=p)


productslist = get_impcervereros_products()
print('Loading on Elasticsearch index')
load_on_elasticsearh(productslist)
pprint(productslist)
# output(productslist)