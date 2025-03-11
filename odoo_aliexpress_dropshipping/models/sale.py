
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_dropshipping_order = fields.Boolean(string="Drop Shipping", compute="_compute_is_dropshipping_order", store=True)

    @api.depends('order_line.is_dropshipping_line')
    def _compute_is_dropshipping_order(self):
        for order in self:
            order.is_dropshipping_order = False
            if order.order_line and order.order_line.filtered("is_dropshipping_line"):
                order.is_dropshipping_order = True

    def create_sale_order_on_aliexpress(self):
        for rec in self:
            url = ''
            product_ids = []
            for line in rec.order_line.filtered('is_dropshipping_line'):
                if url == '' and line.product_id.ali_url:
                    url += line.product_id.ali_url
                product_ids.append(str(line.id) + '_' + str(line.product_id.id))
            url += '?wk_odoo_order_id=' + str(rec.id) + '&wk_odoo_product_ids=' + '__'.join(product_ids)
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_dropshipping_line = fields.Boolean(string='Drop Shipping', related="product_id.is_drop_ship_product")

    def _action_launch_stock_rule(self):
        lines = self.filtered(lambda sol: not sol.is_dropshipping_line)
        return super(SaleOrderLine, lines)._action_launch_stock_rule()
