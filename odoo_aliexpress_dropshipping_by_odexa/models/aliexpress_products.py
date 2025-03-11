
from odoo import models, fields, api, _
from .pro_data_fetch import *

import logging
_logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
from datetime import timedelta
import requests
import time
import json


class AliexpressProducts(models.Model):
    _name = "aliexpress.product"
    _description = "Aliexpress Products"

    name = fields.Char(string="Name", required=True)
    state = fields.Selection(selection=[('new','New'),('need_update','Need To Update'),('deleted','Deleted'),('updated','Updated')], string="Status", default="new")
    description = fields.Text(string="Description")
    title = fields.Char(string="Title")
    ali_product_id = fields.Char(string="Product ID")
    product_url = fields.Char(string="Product URL", required=True)
    price = fields.Char(string="Aliexpress Price", help="This price is aliexpress price fetch according to country or currency selected on aliexpress site while importing product.")
    shipping_from = fields.Char(string="Shipping From")
    shipping_time = fields.Char(string="Aliexpress Shipping Time", help="This shipping time is aliexpress shipping time fetch according to country or currency selected on aliexpress site while importing product.")
    product_images = fields.One2many("ali.product.image","product_id",string="Images")
    product_id = fields.Many2one("product.template", string="Related Product")
    aliexpress_feed_data = fields.Text("Aliexpress Feed Data")
    ali_feed_last_updated = fields.Datetime("Last Updated")

    def create_images_from_feed(self):
        for rec in self.filtered('product_id'):
            img_urls = rec.product_images.mapped('name')
            rec.product_id.update_product_images_from_urls(img_urls)

    def get_aliexpress_product_url_with_en(self):
        self.ensure_one()
        if self.ali_product_id:
            url = "https://www.aliexpress.com/item/"+str(self.ali_product_id)+".html"
        else:
            url = self.product_url
        return url

    def fetch_product_feed_data_from_aliexpress(self):
        self.ensure_one()
        ali_data = self.fetch_product_data_from_aliexpress()
        ali_data = json.dumps(ali_data)
        self.write({
            'aliexpress_feed_data': ali_data,
            'ali_feed_last_updated': fields.Datetime.now(),
            'state': 'need_update'
        })

    def manual_fetch_and_update_feed_data_in_product(self):
        self.fetch_product_feed_data_from_aliexpress()
        self.create_update_product_from_aliexpress()
        return

    @api.model
    def fetch_and_update_product_feed_data_from_aliexpres(self):
        time_delay = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_time_delay')
        FETCH_LIMIT = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_batch_count')
        fetch_days_gap = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_days_gap')
        if not time_delay:
            time_delay = 60
        if not FETCH_LIMIT:
            FETCH_LIMIT = 5
        if not fetch_days_gap:
            fetch_days_gap = 1
        gap_date = fields.Datetime.now() - timedelta(days=fetch_days_gap)
        updated_ids=[]
        while(True):
            records = self.search(['|',('ali_feed_last_updated','=',None),('ali_feed_last_updated','<=',gap_date),('id', 'not in', updated_ids)],limit=FETCH_LIMIT)
            if records:
                updated_ids.extend(records.ids)
                for rec in records:
                    try:
                        rec.fetch_product_feed_data_from_aliexpress()
                    except Exception as e:
                        _logger.info("======Aliexpress=Exception===%r======",e)
                self.env.cr.commit()
                time.sleep(time_delay)
            else:
                break

    @api.model
    def create_or_update_product_data_from_feed(self):
        FETCH_LIMIT = 50
        updated_ids = []
        while(True):
            records = self.search([('state','=','need_update'),('id', 'not in', updated_ids)], limit=FETCH_LIMIT)
            if records:
                updated_ids.extend(records.ids)
                for rec in records:
                    try:
                        rec.create_update_product_from_aliexpress()
                    except Exception as e:
                        _logger.info("======Aliexpress=Exception===%r======",e)
                self.env.cr.commit()
            else:
                break

    def fetch_custom_data_from_aliexpress(self, soup, ship_from=None):
        return {}

    def fetch_product_data_from_aliexpress(self):
        """Fetch product data from aliexpress based on configuration"""
        config_setting_obj = self.env['res.config.settings'].get_values()
        data = {}
        url = self.get_aliexpress_product_url_with_en()
        ship_from = self.shipping_from
        try:

            response = requests.get(url)
            soup = BeautifulSoup(response.content,'lxml')


        except Exception as e:
            error = "Exception during data fetch: %s" % e
            return {
                'error': error
            }
        if config_setting_obj.get('ds_fetch_images') and self.product_id:
            data.update({
                'img_urls' : get_product_image_urls(soup)
            })
        if config_setting_obj.get('ds_fetch_feature'):
            data.update({
                'feature' : get_product_features_html(soup)
            })
        if config_setting_obj.get('ds_fetch_description'):
            data.update({
                'web_description' : get_product_website_description(soup)
            })
        # if config_setting_obj.get('ds_fetch_packaging'):
        #     data.update({
        #         'packaging' : get_product_packaging(soup)
        #     })
        if config_setting_obj.get('ds_auto_published'):
            data.update({
                'published' : True
            })

        data.update({
            'attrs' : get_product_combination_data(soup, ship_from),
            'var_prices' : get_pro_combination_qty_price(soup, ship_from),
        })
        custom_data = self.fetch_custom_data_from_aliexpress(soup, ship_from)
        if custom_data:
            data.update(custom_data)
        return data

    @api.model
    def get_config_updated_price(self, price):
        config_setting_obj = self.env['res.config.settings'].get_values()
        if config_setting_obj.get('ds_price_options') == 'custom':
            price = config_setting_obj.get('ds_custom_price')
        else:
            if config_setting_obj.get('ds_price_options') != 'same':
                per = config_setting_obj.get('ds_price_perc')
                if config_setting_obj.get('ds_price_options') == 'incr':
                    price = price*(1+per/100)
                else:
                    price = price*(1-per/100)
        return price

    def create_product_from_data(self, vals):
        """Create product template and assign attribues"""
        values = {
            'name' : vals['name'],
            'is_drop_ship_product' : True,
            'ali_pro_id' : vals['ali_pro_id'],
            'ali_url' : vals['ali_url'],
            'type' : 'product',
            'purchase_ok' : False,
            'list_price' : 0,
            'ali_shipping_time' : vals['shipping_time'],
            'website_description' : vals['website_description'],
            'allow_out_of_stock_order' : True,
        }
        if vals.get('published'):
            values['website_published'] = True
        product_obj = self.env["product.template"].sudo().create(values)
        return product_obj.id

    def update_product_from_data(self, vals):
        """Update product template and assign attribues"""
        res = self.product_id.write({
            'website_description' : vals['website_description']
        })
        return res

    def update_variants_price_qty(self, price_list):
        variant_objs = self.product_id.product_variant_ids
        temp_values_objs = variant_objs.mapped('product_template_attribute_value_ids')
        attr_objs = temp_values_objs.mapped('attribute_id')
        for var in price_list:
            price = self.get_config_updated_price(float(var['price']))
            if not var.get('var'):
                self.product_id.product_variant_id.update_alipro_price_and_qty(price=price, qty=float(var['qty']), from_currency=var.get('currency'))
            else:
                temp_attr_value_ids = []
                for attr_val_comb in var['var'].split(";"):
                    attr_val = attr_val_comb.split(":")
                    attr = attr_val[0]
                    val = attr_val[1]
                    attr_id = attr_objs.filtered(lambda a: a.comb_id == attr)
                    if attr_id:
                        attr_id = attr_id[0]
                    val_id = temp_values_objs.filtered(lambda a_val: a_val.attribute_id.id == attr_id.id and a_val.product_attribute_value_id.comb_id == val)
                    if val_id:
                        temp_attr_value_ids.append(val_id[0].id)
                variant_obj = variant_objs.filtered(lambda var: set(var.product_template_attribute_value_ids.ids) == set(temp_attr_value_ids))
                variant_obj.update_alipro_price_and_qty(price=price, qty=float(var['qty']), from_currency=var['currency'])
        self.product_id.list_price = self.product_id.product_variant_id.lst_price
        return True

    def update_deleted_aliexpress_products(self):
        self.state = 'deleted'
        product_id = self.product_id
        if product_id:
            product_id.is_published = False
        return True


    def create_update_product_from_aliexpress(self):
        """Create product in odoo store from Aliexpress product feed if product is not created,
        and if already created then updated all its data, Combinations and their price.
        Can be used in cron for creating and updating product from aliexpress automated using aliexpress product feed."""
        self.ensure_one()
        aliexpress_data = self.aliexpress_feed_data
        if aliexpress_data:
            data = json.loads(aliexpress_data)
        else:
            return True
        if data.get('error'):
            return True
        vals = {}
        if not data.get('attrs'):
            self.update_deleted_aliexpress_products()
            return True
        website_description = '<div class="container">'

        if data.get('feature'):
            website_description += '<div class="ali_desc_title">Product Features</div>'
            website_description += data['feature']
        if data.get('web_description'):
            website_description += '<div class="ali_desc_title">Product Description</div>'
            website_description += data['web_description']
        if data.get('packaging'):
            website_description += '<div class="ali_desc_title">Product Packaging Details</div>'
            website_description += data['packaging']
        website_description += '</div>'
        if self.product_id:
            vals = {
                'website_description' : website_description
            }

            self.update_product_from_data(vals)
            if data.get('img_urls'):
                self.product_id.update_product_images_from_urls(data['img_urls'])
        else:
            vals = {
                'name' : self.name,
                'ali_pro_id' : self.ali_product_id,
                'ali_url' : self.get_aliexpress_product_url_with_en(),
                'published' : data.get('published'),
                'shipping_time' : self.shipping_time,
                'website_description' : website_description
            }

            self.product_id = self.create_product_from_data(vals)
            self.create_images_from_feed()
        self.product_id.create_product_variants_from_data(data['attrs'], self.ali_product_id)
        self.update_variants_price_qty(data['var_prices'])

        if self.product_id and self.state != 'updated':
            self.state = 'updated'
        return True

    def product_need_to_be_updated(self):
        for rec in self.filtered(lambda l: l.state in ['updated']):
            rec.state = 'need_update'

    def open_aliexpress_product_url(self):
        self.ensure_one()
        product_url = self.get_aliexpress_product_url_with_en()
        if product_url:
            return {
                'type': 'ir.actions.act_url',
                'url': product_url,
                'target': 'new',
            }

class AliProductImage(models.Model):
    _name = "ali.product.image"
    _description = "Aliexpress Product Images"

    name = fields.Char(string="Image URL")
    product_id = fields.Many2one("aliexpress.product",string="Product")
