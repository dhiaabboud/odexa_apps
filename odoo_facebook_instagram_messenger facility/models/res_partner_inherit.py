from odoo import fields, models


class SocialMediaResPartner(models.Model):
    _inherit = "res.partner"

    id_social_media = fields.Char("Social Media Id")
    social_media_channel_profile_line_ids = fields.One2many(
        comodel_name="social.media.channel.profile.line",
        inverse_name="partner_id",
        string="Social Media Channel Profile Line",
    )


class SocialMediaChannelProfileLineResPartner(models.Model):
    _name = "social.media.channel.profile.line"

    social_media_profile_id = fields.Many2one(
        comodel_name="social.media.profile", string="Social Media Profile"
    )
    channel_id = fields.Many2one(comodel_name="discuss.channel", string="Channel")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
