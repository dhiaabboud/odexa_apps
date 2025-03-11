from odoo import models, fields, api


class InheritUsers(models.Model):
    _inherit = 'res.users'

    sl_slack_user_id = fields.Char('Slack User Id')
    sl_slack_user_name = fields.Char('Slack Username', readonly=True)
    sl_inbox_id = fields.Char('Slack Inbox Id')
