
import requests
import re
import json
import bs4
from bs4 import BeautifulSoup

import logging
_logger = logging.getLogger(__name__)

def get_script_data(soup):
    data = {}
    try:
        main_script = ""
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                if "window.runParams" in script.string:
                    main_script = script
                    break
        main_script = main_script.string
        index = main_script.find('data:')
        end = main_script.find('};\n')
        if index > -1:
            main_script = main_script[index+5:end-1]
        main_script = main_script.strip()
        data = json.loads(main_script)
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product script data: %r~~~~~~~~~~~~~~~",e)
        pass
    return data

def remove_dimension(url):
    return re.sub(r'.jpg_[\d]+x[\d]+.jpg$', ".jpg", url)

def get_product_image_urls(soup):
    """Return a list of product images URL's"""
    imagePathList = []
    try:
        scr_obj = get_script_data(soup)
        imageModule = scr_obj.get('imageComponent')
        imagePathList = imageModule.get('imagePathList')
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product image urls: %r~~~~~~~~~~~~~~~",e)
        pass
    return imagePathList

def get_product_combination_data(soup, ship_from=None):
    """Return available product attributes(with id) and their values(with id).
        Return type dict.
        e.g. :- [{'values': [{'dis_name': 'Standard Package', 'id': 200003982, 'name': 'Bundle 1'}, {'dis_name': 'Add 32GB TF Card', 'id': 200003983, 'name': 'Bundle 2'}, {'dis_name': 'Add 64GB TF Card', 'id': 200003984, 'name': 'Bundle 3'}, {'dis_name': 'Add Orig Miband 3', 'id': 200003985, 'name': 'Bundle 4'}, {'dis_name': 'Add Orig MiEarphone', 'id': 200003986, 'name': 'Bundle 5'}], 'attr': {'name': 'Bundle', 'id': 200000828}}, {'values': [{'dis_name': 'Black 3GB 32GB', 'id': 10, 'name': 'Red'}, {'dis_name': 'Blue 3GB 32GB', 'id': 691, 'name': 'Gray'}, {'dis_name': 'Red 3GB 32GB', 'id': 173, 'name': 'Blue'}], 'attr': {'name': 'Color', 'id': 14}}, {'values': [{'dis_name': 'China', 'id': 201336100, 'name': 'China'}], 'attr': {'name': 'Ships From', 'id': 200007763}}]
    """
    data = []
    try:
        ship_from = ship_from.lower().replace(' ','') if ship_from else ship_from
        scr_obj = get_script_data(soup)

        skuModule = scr_obj.get('skuComponent')
        productSKUPropertyList = skuModule.get('productSKUPropertyList')
        for proPro in productSKUPropertyList:

            attr_name = proPro.get('skuPropertyName')
            shipping_attr = attr_name.lower().replace(' ','') == 'shipsfrom'
            val_data = []
            for proVal in proPro.get('skuPropertyValues'):
                if ship_from and shipping_attr:
                    display_name = proVal.get('propertyValueDisplayName')
                    if display_name.lower().replace(' ','') == ship_from:
                        val_data.append({
                            'id' : proVal.get('propertyValueId'),
                            'name' : proVal.get('propertyValueName'),
                            'dis_name' : display_name
                        })
                else:
                    val_data.append({
                        'id' : proVal.get('propertyValueId'),
                        'name' : proVal.get('propertyValueName'),
                        'dis_name' : proVal.get('propertyValueDisplayName')
                    })
            data.append({
                'attr' : {
                    'name' : attr_name,
                    'id' : proPro.get('skuPropertyId')
                },
                'values' : val_data
            })
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product combination data: %r~~~~~~~~~~~~~~~",e)
        pass
    return data

def get_shipfrom_attr_n_value_id(soup, ship_from):
    """
        Return e.g:- {'attr': {'id': 200007763, 'name': u'Ships From'},
            'value': {'id': 201336106, 'dis_name': u'United States', 'name': u'United States'}}
    """
    try:
        ship_from = ship_from.lower().replace(' ','')
        scr_obj = get_script_data(soup)
        skuModule = scr_obj.get('skuModule')
        productSKUPropertyList = skuModule.get('productSKUPropertyList')
        shipping_data = list(filter(lambda dic: dic['skuPropertyName'].lower().replace(' ','') == 'shipsfrom', productSKUPropertyList))
        if shipping_data:
            shipping_data = shipping_data[0]
            shipping_val = shipping_data.get('skuPropertyValues')
            shipping_val_data = list(filter(lambda dic: dic['propertyValueDisplayName'].lower().replace(' ','') == ship_from, shipping_val))
            if shipping_val_data:
                shipping_val_data = shipping_val_data[0]
                return {
                    'attr' : {
                        'id' : shipping_data.get('skuPropertyId'),
                        'name' : shipping_data.get('skuPropertyName'),
                    },
                    'value' : {
                        'id' : shipping_val_data.get('propertyValueId'),
                        'name' : shipping_val_data.get('propertyValueName'),
                        'dis_name' : shipping_val_data.get('propertyValueDisplayName')
                    }
                }
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product combination ID's: %r~~~~~~~~~~~~~~~",e)
        pass
    return False

def get_sku_amount(skuPriceVal):
    price = 0.0
    currency = None
    skuActivityAmount = skuPriceVal.get('skuActivityAmount', False)
    skuAmount = skuPriceVal.get('skuAmount', False)
    if skuActivityAmount:
        price = skuActivityAmount['value']
        currency = skuActivityAmount['currency']
    elif skuAmount:
        price = skuAmount['value']
        currency = skuAmount['currency']
    return {
        'price' : price,
        'currency' : currency,
    }

def get_pro_combination_qty_price(soup, ship_from=None):
    """Return: Product variants quantity and price.
        Return type List.
        e.g. :- [{'price': 100, 'var': '200000828:200003982;14:10;200007763:201336100', 'qty': '172.99'}, {'price': 20, 'var': '200000828:200003983;14:10;200007763:201336100', 'qty': '185.99'}]
    """
    data = []
    ship_attr_id, ship_val_id = False, False
    try:
        scr_obj = get_script_data(soup)
        if ship_from:
            shipping_data = get_shipfrom_attr_n_value_id(soup, ship_from)
            if shipping_data:
                ship_attr_id = str(shipping_data['attr']['id'])
                ship_val_id = str(shipping_data['value']['id'])
        skuModule = scr_obj.get('priceComponent')
        for skuPrice in skuModule.get('skuPriceList'):
            skuAttr = skuPrice.get('skuAttr')
            skuVal = skuPrice.get('skuVal')
            skuAttr = re.sub(r'#[^;]+', "", skuAttr)
            if ship_from and ship_attr_id and ship_attr_id in skuAttr:
                if ship_val_id and ship_val_id in skuAttr:
                    sku_amount = get_sku_amount(skuVal)
                    data.append({
                        'var' : skuAttr,
                        'price' : sku_amount['price'],
                        'currency' : sku_amount['currency'],
                        'qty' : skuVal['availQuantity']
                    })
            else:
                sku_amount = get_sku_amount(skuVal)
                data.append({
                    'var' : skuAttr,
                    'price' : sku_amount['price'],
                    'currency' : sku_amount['currency'],
                    'qty' : skuVal['availQuantity']
                })
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product combination price & price: %r~~~~~~~~~~~~~~~",e)
        pass
    return data

def get_product_website_description(soup):
    """Return: HTML code of product website description section"""
    web_desc = ''
    try:
        scr_obj = get_script_data(soup)
        descriptionModule = scr_obj.get('productDescComponent')
        descriptionUrl = descriptionModule.get('descriptionUrl')
        soup2 = BeautifulSoup(requests.get(descriptionUrl).content,'lxml')
        body = soup2.body
        for kse in body.find_all('kse:widget'):
            kse.decompose()

        for script in body('script'):
            script.decompose()

        body.hidden = True
        web_desc = body.prettify()
    except Exception as e:
        _logger.info("~~~~~~~~Error during fetching product description: %r~~~~~~~~~~",e)
        pass
    return web_desc

def get_product_features(soup):
    """Return: List of features.
        e.g. :- [{'name': 'Unlock Phones', 'values': 'Yes'}, {'name': 'Display Resolution', 'values': '2340x1080'}, {'name': 'Language', 'values': 'Norwegian,Italian,Arabic,French,German,Russian,Japanese,Spanish,Polish,English,Portuguese,Korean,Turkish'}]
    """
    feature_data = []
    try:
        scr_obj = get_script_data(soup)
        specsModule = scr_obj.get('productPropComponent')
        for prop in specsModule.get('props'):
            feature_data.append({
                'name' : prop.get('attrName'),
                'values' : prop.get('attrValue')
            })
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product features: %r~~~~~~~~~~~~~~~",e)
        pass
    return feature_data

def get_product_features_html(soup):
    html = ""
    feature_list = get_product_features(soup)
    if feature_list:
        html = "<ul class='row ali_pro_feature'>"
        for feature in feature_list:
            html += "<li class='col-6'><span class='title'>"+feature['name']+': '+"</span><span class='desc'>"+feature['values']+"</span></li>"
        html += "</ul>"
    return html

def get_product_packaging(soup):
    """Return: HTML code of product packaging section"""
    pack_data = ""
    try:
        desc_main_div = soup.find('div',{'id':'j-product-desc'})
        pack_div = desc_main_div.find('div',{'class':'ui-box pnl-packaging-main'})
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product packaging: %r~~~~~~~~~~~~",e)
        pass
    return pack_data

def get_product_details(url):
    data = {'success' : False}
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content)
        scr_obj = get_script_data(soup)
        images = get_product_image_urls(soup)
        title = soup.find("title").string
        desc = soup.find('meta',{'name':'description'})['content']
        # product price
        priceModule = scr_obj.get('priceModule')
        price = priceModule.get('formatedActivityPrice')
        # shipping From
        comb_data = get_product_combination_data(soup)

        shipping_data = list(filter(lambda dic: dic['attr']['name'].lower().replace(' ','') == 'shipsfrom', comb_data))
        ship_from = []
        if shipping_data:
            for val in shipping_data[0]['values']:
                ship_from.append({
                    'sku' : val['id'],
                    'value' : val['dis_name'],
                })
        data = {
            'img' : images,
            'price' : price,
            'desc' : desc,
            'title' : title,
            'product_url' : url,
            'ship_from' : ship_from,
            'comb_product' : True if comb_data else False,
            'success' : True,
        }
    except Exception as e:
        _logger.info("~~~~~~~~~~Error during fetching product details: %r~~~~~~~~~~~~~~~",e)
        pass
    return data
