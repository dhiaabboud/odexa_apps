from odoo import fields, models


class SocialMediaProfile(models.Model):
    _name = "social.media.messages"
    _rec_name = "message"

    message = fields.Char(string="Message", readonly=True)
    social_media_type = fields.Selection(
        [("instagram", "Instagram"), ("messenger", "Messenger")], "Social Media Type"
    )
    from_partner_id = fields.Many2one("res.partner", "From Partner")
    to_partner_id = fields.Many2one("res.partner", "To Partner")

    def get_follower_data(self):
        return True
