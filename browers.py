# coding=UTF-8
# Script for scrap browers insumos cerveceros

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from pprint import pprint
from elasticsearch import Elasticsearch, helpers
import unidecode

base_url = 'https://www.browersinsumos.com.ar'

def fetch_page(url):    
    headers = {'user-agent': 'Chrome/89.0.4389.114'}
    r = requests.get( url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup

def get_category_page(category):
    headers = {'user-agent': 'Chrome/89.0.4389.114'}
    data = {"categoria": category}

    r = requests.post( base_url + '/assets/controller/productosXCategoria.php',data=data, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup

def parse_subcategories(category_soup):
    subcategories = []
    results = category_soup.find_all('div', {'class': 'list-group-item'})
    for item in results:
        subcategories.append({
            'id': int(re.search(r'(\d+)', str(item)).group(0)),
            'name': item.text.strip()
        })
    return subcategories

def get_categories():
    categories = []
    soup = fetch_page(base_url)
    lis = soup.find('ul', id='menu').find_all('li')
    for li in lis:
        categories.append({
            'id': int(li.find('input', {'name':'categoria'})['value']),
            'name': li.find('a').text
        })
        # s = soup.find('ul', id='menu').find_all('input', {'name':'categoria'})
    return categories


def get_items_by_subcategory(subcategory_id):
    headers = {'user-agent': 'Chrome/89.0.4389.114'}
    data = {"subcat": subcategory_id}

    r = requests.post( base_url + '/assets/controller/Productos/productos_x_subcat.php',data=data, headers=headers)
    subcat_page = BeautifulSoup(r.text, 'html.parser')
    item_boxes = subcat_page.find_all('div',{'class': 'col-lg-4 col-md-4 col-sm-6 col-xs-12'})

    modal_position = 0
    products = []
    for item in item_boxes:
        product_id = 0

        # If the box has onclick event, it's on stock and we can get the product_id. If doesn't have an onclick handler, we can't get the product_id
        # Skip for now out-of-stock products 
        if item.has_attr('onclick'):
            product_id = int(re.search(r'llamar_kilaje\((.+),(.+)\);', item['onclick']).group(2)) # Get Product ID from function call on onclick event

            name = item.find('h6', {'class': 'titulo_producto'}).text
            img_link = item.find('img', {'class': 'img-responsive'})['src'].replace('../', '/assets/')
            modal = subcat_page.find('div', id='myModal' + str(modal_position))
            description = modal.find('p', {'class': 'new_font'}).text
            description = description.replace('Debido a los cambios constantes en el valor del dolar, algunos precios pueden estar desactualizados.','')
            description = description.replace('*Los precios pueden sufrir modificaciones sin previo aviso.','')
            description = description.replace('\n','')
            description = description.replace('\r','').strip()

            price = modal.find('div', 'modal-footer').find('span', {'class':'new_font'}).text.replace('\n', '').strip()
            price = price.replace('Unid.', '')
            price = price.replace('$', '').strip()
            if ((str(price) != '')):
                price = float(price)
            else:
                price_from_dropdown = get_price_from_dropdown(product_id)
                price = price_from_dropdown['value'] if price_from_dropdown else 0

            products.append({
                'product_id': product_id,
                'name': name,
                'description': description,
                'link': base_url,
                'price': (price),
                'img_url': base_url + img_link,
                'in_stock': 'yes'
            })
        modal_position += 1

    return products

def get_price_from_dropdown(product_id):
    headers = {'user-agent': 'Chrome/89.0.4389.114'}
    data = {"id_prod": product_id}

    r = requests.post( base_url + '/assets/controller/Productos/productos_x_kg.php',data=data, headers=headers)
    prices = BeautifulSoup(r.text, 'html.parser')
    options = prices.find_all('option')
    if (options):
        last_price_value = options[-1]['value']
        price = {
            "value": float(last_price_value.split('-')[1]),
            "unit": int(last_price_value.split('-')[0]) / 1000
        }
    else:
        price = None

    return price

    

def parse_kits(kits_page):
    item_boxes = kits_page.find_all('div',{'class': 'col-lg-3 col-md-4 col-sm-6 col-xs-12'})
    modal_position = 0
    products = []

    for item in item_boxes:

        name = item.find('h6').text
        product_id = unidecode.unidecode(name.strip().replace(' ', '_').lower())

        img_link = item.find('div', 'contenedor_imagen').find('img')['src'].replace('../', '/assets/')
        modal = kits_page.find('div', id='myModalkit' + str(modal_position))
        description = modal.find('p', {'class': 'new_font'}).text
        description = description.replace('Debido a los cambios constantes en el valor del dolar, algunos precios pueden estar desactualizados.','')
        description = description.replace('*Los precios pueden sufrir modificaciones sin previo aviso.','')
        description = description.replace('\n','')
        description = description.replace('\r','').strip()

        price = modal.find('div', 'modal-footer').find('span', {'class':'new_font'}).text.replace('\n', '').strip()
        price = price.replace('Subtotal', '')
        price = price.replace('$', '').strip()
        price = float(price) if (str(price) != '') else float(0)

        modal_position += 1
        products.append({
            'product_id': product_id,
            'name': name,
            'description': description,
            'link': base_url,
            'price': (price),
            'img_url': base_url + img_link,
            'in_stock': 'yes'
        })
    return products

def parse_sets(sets_page):
    item_boxes = sets_page.find_all('div',{'class': 'col-lg-3 col-md-4 col-sm-6 col-xs-12'})
    modal_position = 0
    products = []

    for item in item_boxes:

        name = item.find('h6').text
        product_id = unidecode.unidecode(name.strip().replace(' ', '_').lower())

        img_link = item.find('div', 'contenedor_imagen').find('img')['src'].replace('../', '/assets/')
        modal = sets_page.find('div', id='myModal' + str(modal_position))
        description = modal.find('p', {'class': 'new_font'}).text
        description = description.replace('Debido a los cambios constantes en el valor del dolar, algunos precios pueden estar desactualizados.','')
        description = description.replace('*Los precios pueden sufrir modificaciones sin previo aviso.','')
        description = description.replace('\n','')
        description = description.replace('\r','').strip()

        price = modal.find('div', 'modal-footer').find('span', {'class':'new_font'}).text.replace('\n', '').strip()
        price = price.replace('Subtotal', '')
        price = price.replace('$', '').strip()
        price = float(price) if (str(price) != '') else float(0)

        modal_position += 1
        products.append({
            'product_id': product_id,
            'name': name,
            'description': description,
            'link': base_url,
            'price': (price),
            'img_url': base_url + img_link,
            'in_stock': 'yes'
        })
    return products

def get_browers_products():
    all_prods = []
    categories = get_categories()
    for categoria in categories:
        soup = get_category_page(categoria['id'])
        subcategories = parse_subcategories(soup)

        if (not subcategories):
            # Parse kits
            if (categoria['id'] == 5):
                prods = parse_kits(soup)
                for p in prods:
                    p['primary_category'] = categoria['name']
                    p['secondary_category'] = ''
                    p['provider'] = 'browers'
                    all_prods.append(p)

            # Parse sets
            if (categoria['id'] == 12):
                prods = parse_sets(soup)
                for p in prods:
                    p['primary_category'] = categoria['name']
                    p['secondary_category'] = ''
                    p['provider'] = 'browers'
                    all_prods.append(p)

            # TODO parse libros category
        else:
            for subcat in subcategories:
                prods = get_items_by_subcategory(subcat['id'])
                for p in prods:
                    p['primary_category'] = categoria['name']
                    p['secondary_category'] = subcat['name']
                    p['provider'] = 'browers'
                    all_prods.append(p)
    return all_prods

def load_bulk_on_elasticsearch(products):
    bulk_body = [];
    for p in products:
        bulk_body.append({
            "_index": 'items',
            "_id" : 'browers_' + str(p['product_id']),
            "_source": p,
        });

    es = Elasticsearch([{'host': 'es_elgranbazarcervecero', 'port': 9200}])
    helpers.bulk(es, bulk_body);



##
## Fetch and load on ES
##
pprint('Fetching Products for Browers')
products = get_browers_products();
pprint('Loading on Elasticsearch')
load_bulk_on_elasticsearch(products)
pprint('Load complete')