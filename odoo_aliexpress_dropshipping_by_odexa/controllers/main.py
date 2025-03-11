
from odoo import http, _
from odoo.http import request
from odoo.addons.odoo_aliexpress_dropshipping.models.pro_data_fetch import get_product_details

import werkzeug
import json
import re

import logging
_logger = logging.getLogger(__name__)

class AliexpressProducts(http.Controller):

    def _add_aliexpress_product(self, vals):
        aliProduct = request.env["aliexpress.product"]
        config_setting_obj = request.env['res.config.settings'].get_values()
        data = {'product_id': False, 'status' : 'fail', 'msg' : 'Error','success': False}
        try:
            product_obj = aliProduct.search([('ali_product_id','=',vals.get('product_id'))], limit=1)
            if not product_obj:
                values = {
                    'name' : vals.get('product_name'),
                    'description' : vals.get('meta_desc'),
                    'title' : vals.get('meta_title'),
                    'ali_product_id' : vals.get('product_id'),
                    'product_url' : vals.get('product_url'),
                    'price' : vals.get('price'),
                    'shipping_from' : vals.get('ship_from'),
                    'shipping_time' : vals.get('shipping_time'),
                    'state' : 'new',
                }
                product_obj = aliProduct.create(values)
                for img_url in vals.get('images'):
                    request.env["ali.product.image"].create({
                        'name' : img_url,
                        'product_id' : product_obj.id
                    })
                if config_setting_obj.get('ds_instant_product'):
                    product_obj.with_context(lang=None).manual_fetch_and_update_feed_data_in_product()

                data.update({
                    'product_id' : product_obj.id,
                    'status' : 'created',
                    'msg' : 'Created',
                    'success' : True
                })
            else:
                data.update({
                    'product_id' : product_obj.id,
                    'status' : 'exist',
                    'msg' : 'Already Exist',
                    'success' : True
                })
        except Exception as e:
            _logger.info("===========Exception===%r================",e)
        return data

    def _authenticate_user_data(self, vals):
        aliexpress_token = vals.get('password')
        db_name = request.session.db
        uid = False
        if not aliexpress_token and not db_name:
            return False
        user = request.env["res.users"].sudo().search([('aliexpress_token','=',aliexpress_token)], limit=1)
        if user:
            user_id = user.id
            if user.sudo().has_group('odoo_aliexpress_dropshipping.odoo_aliexpress_dropshipping_group'):
                request.update_env(user=user_id)
                uid = user_id
        return uid

    def get_ali_sale_order_data(self, product_id, line_id, next_pro_id):
        proPro = request.env["product.product"]
        product_obj = proPro.browse(int(product_id))
        line_obj = request.env["sale.order.line"].browse(int(line_id))
        data = {
            'qty' : line_obj.product_uom_qty,
            'product_url' : ''
        }
        comb_list = []
        for attr in product_obj.product_template_attribute_value_ids:
            comb_list.append({
                'group_sku' : attr.attribute_id.name,
                'attribute_sku' : attr.name,
            })
        data.update({
            'combination_sku' : comb_list
        })
        if next_pro_id:
            next_product_obj = proPro.browse(int(next_pro_id))
            data.update({
                'product_url' : next_product_obj.ali_url
            })
        return data

    def _response(self, callback, body):
        body = callback+'('+json.dumps(body)+')'
        headers = [
            ('Content-Type', 'application/javascript; charset=utf-8'),
            ('Content-Length', len(body))
        ]
        return werkzeug.wrappers.Response(body, headers=headers)

    @http.route('/odoo/aliexpress/dropship', csrf=False, type='http', auth="none", methods=['GET'])
    def odoo_aliexpress_dropship(self, **post):
        method = post.get('method')
        arguments = json.loads(post.get('arguments'))
        callback = post.get('callback')
        data = {'success': False}

        if not method and not callback:
            return request.not_found()

        if method == 'authenticate':
            uid = self._authenticate_user_data(arguments)
            data['success'] = True if uid else False

        if method == 'addAliexpressProduct':
            uid = self._authenticate_user_data(arguments)
            if uid:
                args = arguments
                args.pop('password')
                args['uid'] = uid
                pro_data = self._add_aliexpress_product(args)
                data.update(pro_data)

        if method == 'getOrderDetails':
            uid = self._authenticate_user_data(arguments)
            if uid:
                order_id = arguments.get('order_id')
                pro_ids = arguments.get('product_id')
                next_pro_ids, next_pro_id = False, False
                line_pro_list = pro_ids.split('__')
                product_id = line_pro_list[0].split('_')[1]
                line_id = line_pro_list[0].split('_')[0]
                if len(line_pro_list) > 1:
                    next_pro_id = line_pro_list[1].split('_')[1]
                    next_pro_ids = '__'.join(line_pro_list[1:])
                order_data = self.get_ali_sale_order_data(product_id, line_id, next_pro_id)
                order_data.update({
                    'product_ids' : next_pro_ids,
                    'success': True
                })
                data.update(order_data)

        if method == 'getCustomerAddress':
            uid = self._authenticate_user_data(arguments)
            if uid:
                user_obj = request.env["res.users"].browse(int(uid))
                order_id = arguments.get('order_id')
                order_obj = request.env["sale.order"].browse(int(order_id))
                partner_id = order_obj.partner_id
                data.update({
                    'email' : user_obj.partner_id.email,
                    'country_iso_code' : partner_id.country_id.code if partner_id.state_id else '',
                    'firstname' : partner_id.name,
                    'lastname' : '',
                    'address1' : partner_id.street,
                    'address2' : partner_id.street2,
                    'city' : partner_id.city,
                    'phone_mobile' : re.sub(r'[()]',"",partner_id.mobile) if partner_id.mobile else '',
                    'phone' : re.sub(r'[()]',"",partner_id.phone) if partner_id.phone else '',
                    'postcode' : partner_id.zip,
                    'state_name' : partner_id.state_id.name if partner_id.state_id else '',
                    'success': True
                })

        if method == 'getProductDetails':
            uid = self._authenticate_user_data(arguments)
            if uid:
                url = arguments.get('product_url')
                data = get_product_details(url)
        response = self._response(callback, data)
        return response
