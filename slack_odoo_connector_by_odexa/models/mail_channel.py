# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OdooDiscussions(models.Model):
    _inherit = "discuss.channel"

    sl_slack_channel_id = fields.Char('Slack Channel Id')
