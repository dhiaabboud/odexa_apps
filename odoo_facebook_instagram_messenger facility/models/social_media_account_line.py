from odoo import fields, models


class SocialMediaAccountLine(models.Model):
    _name = "social.media.account.line"
    _description = "Social Media Account Id"

    instagram_account_id = fields.Char("Instagram ID")
    messenger_account_id = fields.Char("Messenger ID")
    partner_id = fields.Many2one("res.partner")
