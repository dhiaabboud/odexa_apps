
from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ds_instant_product = fields.Boolean(string="New Product")
    ds_auto_published = fields.Boolean(string="Auto Published")

    ds_fetch_images = fields.Boolean(string="Fetch Product Images")
    ds_fetch_feature = fields.Boolean(string="Fetch Product Feature")
    ds_fetch_description = fields.Boolean(string="Fetch Product Description")
    ds_fetch_packaging = fields.Boolean(string="Fetch Product Packaging")

    ds_display_shipping_time = fields.Boolean(string="Display Aliexpress Shipping Time")

    ds_price_options = fields.Selection(selection=[('same','Same as AliExpress'),('custom', 'Custom Price'),('incr','Increase'),('decr','Decrease')], string="Price", default="same")
    ds_custom_price = fields.Float()
    ds_price_perc = fields.Float(string="%")
    ds_fetch_time_delay = fields.Integer(string="Fetch Time Delay")
    ds_fetch_batch_count = fields.Integer(string="Fetch Batch Count")
    ds_fetch_days_gap = fields.Integer(string="Fetch Data After(Days)")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_instant_product', self.ds_instant_product)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_feature', self.ds_fetch_feature)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_description', self.ds_fetch_description)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_packaging', self.ds_fetch_packaging)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_display_shipping_time', self.ds_display_shipping_time)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_price_options', self.ds_price_options)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_custom_price', self.ds_custom_price)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_price_perc', self.ds_price_perc)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_auto_published', self.ds_auto_published)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_images', self.ds_fetch_images)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_time_delay', self.ds_fetch_time_delay)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_batch_count', self.ds_fetch_batch_count)
        self.env['ir.default'].sudo().set('res.config.settings', 'ds_fetch_days_gap', self.ds_fetch_days_gap)

    @api.model
    def get_values(self, fields=None):
        res = super(ResConfigSettings, self).get_values()
        ds_instant_product = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_instant_product')
        ds_fetch_feature = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_feature')
        ds_fetch_description = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_description')
        ds_fetch_packaging = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_packaging')
        ds_display_shipping_time = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_display_shipping_time')
        ds_price_options = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_price_options')
        ds_custom_price = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_custom_price')
        ds_price_perc = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_price_perc')
        ds_auto_published = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_auto_published')
        ds_fetch_images = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_images')
        ds_fetch_time_delay = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_time_delay')
        ds_fetch_batch_count = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_batch_count')
        ds_fetch_days_gap = self.env['ir.default'].sudo()._get('res.config.settings', 'ds_fetch_days_gap')
        res.update(
            ds_instant_product = ds_instant_product,
            ds_fetch_feature = ds_fetch_feature,
            ds_fetch_description = ds_fetch_description,
            ds_fetch_packaging = ds_fetch_packaging,
            ds_display_shipping_time = ds_display_shipping_time,
            ds_price_options = ds_price_options,
            ds_custom_price = ds_custom_price,
            ds_price_perc = ds_price_perc,
            ds_auto_published = ds_auto_published,
            ds_fetch_images = ds_fetch_images,
            ds_fetch_time_delay = ds_fetch_time_delay,
            ds_fetch_batch_count = ds_fetch_batch_count,
            ds_fetch_days_gap = ds_fetch_days_gap
        )
        return res
