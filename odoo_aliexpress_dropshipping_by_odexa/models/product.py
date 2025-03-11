
from odoo import models, fields, api, _
import requests
import base64
import urllib.request

import logging
_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    aliexpress_qty = fields.Float("Aliexpress Quantity")

    def _compute_quantities(self):
        super(ProductProduct, self)._compute_quantities()
        for product in self:
            if product.is_drop_ship_product:
                res = product.get_available_stock_qty()
                # product.virtual_available = product.aliexpress_qty
                product.qty_available = res['qty_available']
                product.outgoing_qty = res['outgoing_qty']
                product.virtual_available = res['virtual_available']

    @api.depends('list_price', 'price_extra')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        admin_products = self.filtered(lambda p:not p.is_drop_ship_product)
        ali_products = self - admin_products
        super(ProductProduct, admin_products)._compute_product_lst_price()
        for product in ali_products:
            product.lst_price =  product.price_extra

    def _price_compute(self, price_type, uom=False, currency=False, company=None, date=False):
        admin_products = self.filtered(lambda p: not p.is_drop_ship_product)
        res = super(ProductProduct, admin_products)._price_compute(price_type, uom=uom, currency=currency, company=company, date=date)

        if not uom and self._context.get('uom'):
            uom = self.env['uom.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        products = self - admin_products
        if price_type == 'standard_price':
            products = products.with_company(company or self.env.company).sudo()

        prices = dict.fromkeys(products.ids, 0.0)
        for product in products:
            prices[product.id] = 0.0
            if price_type == 'list_price':
                prices[product.id] += product.price_extra
                if self._context.get('no_variant_attributes_price_extra'):
                    prices[product.id] += sum(self._context.get('no_variant_attributes_price_extra'))

            if uom:
                prices[product.id] = product.uom_id._compute_price(prices[product.id], uom)

            if currency:
                prices[product.id] = product.currency_id._convert(
                    prices[product.id], currency, product.company_id, fields.Date.today())

        res.update(prices)
        return res

    def get_available_stock_qty(self):
        for rec in self:
            total_qty = rec.aliexpress_qty
            order_line = self.env["sale.order.line"].sudo().search([('product_id','=',rec.id),('state','=','sale')])
            sale_qty = sum(order_line.mapped('product_uom_qty'))
            return {
                'qty_available' : total_qty,
                'outgoing_qty' : sale_qty,
                'virtual_available' : total_qty - sale_qty,
            }

    def update_alipro_price_and_qty(self, price, qty, from_currency=None):
        if len(self) == 0:
            return
        if from_currency:
            company_id = self[0].company_id
            if not company_id:
                company_id = self.env.company
            to_currency = self[0].currency_id
            from_currency_obj = self.env["res.currency"].with_context(active_test=False).search([('name','=',from_currency)],limit=1)
            price = from_currency_obj._convert(
                price, to_currency, company_id, fields.Date.today()
            )
        self.write({
            'wk_extra_price' : price,
            'aliexpress_qty' : qty
        })

class ProductTemplate(models.Model):
    _inherit = "product.template"

    ali_pro_id = fields.Char(string="Aliexpress ID")
    ali_url = fields.Char(string="URL")
    is_drop_ship_product = fields.Boolean(string="Imported from Aliexpress")
    aliexpress_total_qty = fields.Float(string="Aliexpress Quantity", compute="_compute_aliexpress_total_qty", store=True)
    ali_shipping_time = fields.Char(string="Shipping Time")

    def update_product_images_from_urls(self, img_urls):
        self.ensure_one()
        ProImage = self.env["product.image"]
        for img_url in img_urls:
            img_obj = self.product_template_image_ids.filtered(lambda img: img.ali_url == img_url)

            if not img_obj:
                try:
                    # image_content = requests.get(img_url).content
                    image_content = urllib.request.urlopen(img_url).read()
                except Exception as e:
                    image_content = b''
                image_data = base64.b64encode(image_content)
                img_obj = ProImage.create({
                        'name' : img_url,
                        'ali_url' : img_url,
                        'image_1920' : image_data,
                        'product_tmpl_id' : self.id
                    })
            if not self.image_1920:
                self.image_1920 = img_obj.image_1920

    @api.depends('product_variant_ids.aliexpress_qty')
    def _compute_aliexpress_total_qty(self):
        for temp in self:
            if temp.product_variant_ids:
                temp.aliexpress_total_qty = sum(temp.product_variant_ids.mapped('aliexpress_qty'))

    def get_aliexpress_value_image_data(self, value):
        img_url_50 = value.get('img_url_50')
        try:
            ali_image = base64.b64encode(requests.get(img_url_50).content) if img_url_50 else None
        except Exception as e:
            _logger.info("============Exception=====%r============",e)
            ali_image = None
        return {
            'ali_image' : ali_image,
            'ali_img_url_50' : img_url_50,
            'ali_img_url_640' : value.get('img_url_640'),
        }

    def create_and_assign_attrs(self, attr, values, ali_pro_id):
        """Search attribute and their values if they are not exist then create new one then after
            search product attribute line corresponding to attribute if exist then update
            attribute values and if not then create a new one."""
        proAttr = self.env["product.attribute"]
        attrsValue = self.env["product.attribute.value"]
        proAttrLine = self.env["product.template.attribute.line"]
        attr_value_ids = []
        image_values = any([v.get('img_url_50') for v in values])
        display_type = 'ali_image' if image_values else 'select'

        attr_obj = proAttr.search([('name','=ilike',attr['name']),('comb_id','=',attr['id'])], limit=1)
        if attr_obj:
            attrs_vals = {}
            if attr_obj.display_type != display_type:
                attrs_vals['display_type'] = display_type
                attr_obj.write({'display_type' : display_type})
        else:
            attr_obj = proAttr.create({'name' : attr['name'], 'display_type' : display_type, 'comb_id' : attr['id']})

        for value in values:
            img_url_50 = value.get('img_url_50')
            val_obj = attrsValue.search([('name','=ilike',value['dis_name']),('attribute_id','=',attr_obj.id),('comb_id','=',value['id']),('ali_pro_id','=',ali_pro_id)], limit=1)

            if val_obj:
                # need to check the images and update the missing images
                if img_url_50 and val_obj.ali_img_url_50 != img_url_50:
                    ali_image_vals = self.get_aliexpress_value_image_data(value)
                    val_obj.write(ali_image_vals)
            else:
                attrsValue_vals = {
                    'name' : value['dis_name'],
                    'attribute_id' : attr_obj.id,
                    'ali_pro_id' : ali_pro_id,
                    'comb_id' : value['id']
                }
                if img_url_50:
                    ali_image_vals = self.get_aliexpress_value_image_data(value)

                    attrsValue_vals.update(ali_image_vals)

                val_obj = attrsValue.create(attrsValue_vals)
            attr_value_ids.append(val_obj.id)

        return {
            attr_obj.id : attr_value_ids
        }

    def add_aliexpress_images_in_variants(self):
        for product in self.product_variant_ids:
            values = product.product_template_attribute_value_ids.mapped('product_attribute_value_id')
            values = values.filtered('ali_img_url_640')
            if values:
                image_url = values[0].ali_img_url_640
                try:
                    ali_image = base64.b64encode(requests.get(image_url).content) if image_url else None
                except Exception as e:
                    ali_image = None
                if ali_image:
                    product.write({'image_1920': ali_image})

    def create_product_variants_from_data(self, attrs, ali_pro_id):
        attr_values_data = {}
        for attr in attrs:
            data = self.create_and_assign_attrs(attr['attr'], attr['values'], ali_pro_id)
            attr_values_data.update(data)

        existing_attr_lines = self.env["product.template.attribute.line"]
        attribute_line_vals = []
        for attr, values in attr_values_data.items():
            attr_line = self.attribute_line_ids.filtered(lambda l: l.attribute_id.id == attr)
            if len(attr_line) > 1:
                attr_line = attr_line[0]
            if attr_line:
                existing_attr_lines = existing_attr_lines + attr_line
                attribute_line_vals.append((1, attr_line.id, {
                    'value_ids': [(6, 0, values)],
                }))
            else:
                attribute_line_vals.append((0, 0, {
                    'attribute_id': attr,
                    'value_ids': [(6, 0, values)],
                }))

        extra_attr_lines = self.attribute_line_ids - existing_attr_lines
        if extra_attr_lines:
            attribute_line_vals.extend([(2, attr_line.id) for attr_line in extra_attr_lines])
        self.write({
            'attribute_line_ids' : attribute_line_vals
        })
        self.add_aliexpress_images_in_variants()
        return True

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    comb_id = fields.Char(string='Aliexpress Comb ID')
    display_type = fields.Selection(selection_add=[('ali_image', 'Aliexpress Image')], ondelete={'ali_image': 'cascade'})

    def name_get(self):
        return [(attr.id, "%s[Ali]" % attr.name) if attr.comb_id else (attr.id, attr.name) for attr in self]

class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    comb_id = fields.Char(string='Aliexpress Comb ID')
    ali_pro_id = fields.Char(string="Aliexpress ID")
    ali_image = fields.Binary("Aliexpress Image")
    ali_img_url_50 = fields.Char(string="Aliexpress URL(50px)")
    ali_img_url_640 = fields.Char(string="Aliexpress URL(640px)")

    _sql_constraints = [('value_company_uniq', 'unique (name, attribute_id, comb_id, ali_pro_id)', "You cannot create two values with the same name for the same attribute.")]

class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    ali_image = fields.Binary("Aliexpress Image", related="product_attribute_value_id.ali_image")
    ali_img_url_50 = fields.Char("Aliexpress URL(50px)", related="product_attribute_value_id.ali_img_url_50")
    ali_img_url_640 = fields.Char("Aliexpress URL(640px)", related="product_attribute_value_id.ali_img_url_640")

class ProductImage(models.Model):
    _inherit = "product.image"

    ali_url = fields.Char(string="Image Url")
