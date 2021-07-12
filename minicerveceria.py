# coding=UTF-8

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint
from elasticsearch import Elasticsearch, helpers

def fetch_page(url):    
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup

def get_minicerveceria_products():
    products = []

    insumos_products = parse_category_page('http://minicerveceria.com/61-insumos')
    for item in insumos_products:
        item['primary_category'] = 'Insumos'
    products = products + insumos_products

    equipos_products = parse_category_page('http://minicerveceria.com/18-equipos')
    for item in equipos_products:
        item['primary_category'] = 'Equipos'
    products = products + equipos_products

    destilados_products = parse_list_page('https://minicerveceria.com/71-destilados')
    for item in destilados_products:
        item['primary_category'] = 'Destilados'
    products = products + destilados_products

    vinos_products = parse_list_page('https://minicerveceria.com/72-vinos')
    for item in vinos_products:
        item['primary_category'] = 'Vinos'
    products = products + vinos_products

    libros_products = parse_list_page('https://minicerveceria.com/74-libros-cursos-gratis')
    for item in libros_products:
        item['primary_category'] = 'Libros'
    products = products + libros_products

    return products


def load_bulk_on_elasticsearch(products):
    bulk_body = [];
    for p in products:
        bulk_body.append({
            "_index": 'items',
            "_id" : 'minicerveceria_' + str(p['product_id']),
            "_source": p,
        });

    es = Elasticsearch([{'host': 'es_elgranbazarcervecero', 'port': 9200}])
    helpers.bulk(es, bulk_body);
    # es.help(index='items',id='imp_' + p['product_id'] , body=p)
    # es.helpper

def parse_list_page(url):
    productslist = []
    product_list_page = fetch_page(url)

    # Check and fecth list with all products 
    if (product_list_page.find(id='nb_item') is not None):
        n = product_list_page.find(id='nb_item').find_all('option')[-1]['value']
        url = url + '?n=' + n
        product_list_page = fetch_page(url)

    product_boxes = product_list_page.find("ul","product_list").find_all("div","product-container")

    for item in product_boxes:

        link = item.find('a', 'product-name')['href']
        product = parse_product_page(link)

        # Fetching stock status
        stock_badge = item.find('span', 'availability')
        if (stock_badge is not None and stock_badge.text.strip() == 'En stock'):
            product['in_stock'] = 'yes'
        elif (stock_badge is not None and stock_badge.text.strip() == 'Agotado'):
            product['in_stock'] = 'no'
        else:
            product['in_stock'] = ''

        productslist.append(product)

    return productslist

def parse_product_page(product_url):

    product_page = fetch_page(product_url)
    product = {
        'provider': 'minicerveceria',
        'description': product_page.find(id='short_description_block').text if product_page.find(id='short_description_block') is not None else '',
        'product_id': int(product_page.find(id='product_page_product_id')['value']),
        'name': product_page.find('div', 'pb-center-column col-xs-12 col-sm-4').find('h1').text.strip().lower(),
        'link': product_url,
        'price': float(product_page.find('div', 'box-info-product').find('span', 'price').text.replace('AR$', '').replace('.','')),
        'img_url': product_page.find(id='bigpic')['src']
    }

    return product

def parse_category_page(url):
    products = []
    category_page = fetch_page(url)
    subcategories = category_page.find(id='subcategories').find_all('li')

    for subcat in subcategories:
        subcat_link = subcat.find('a')['href']
        subcat_name = subcat.find('a', 'subcategory-name').text.lower()
        subcat_products = parse_list_page(subcat_link)
        for p in subcat_products:
            p['secondary_category'] = subcat_name
        products = products + subcat_products
    
    return products
        
pprint('Fetching Minicerveceria items')
productslist = get_minicerveceria_products()
pprint('Loading on Elasticsearch index')
load_bulk_on_elasticsearch(productslist)
pprint('Loaded Minicerveceria on Elasticsearch')