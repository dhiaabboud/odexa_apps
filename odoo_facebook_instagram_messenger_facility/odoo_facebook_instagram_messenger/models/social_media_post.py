import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class InstaPost(models.Model):
    _name = "social.media.post"

    name = fields.Char(string="Media ID")
    caption = fields.Char("Caption")
    post_image = fields.Binary(string="Post Image", attachment=True)
    social_media_profile_id = fields.Many2one("social.media.profile")
    social_media_type = fields.Selection(
        [("instagram", "Instagram"), ("messenger", "Messenger")],
        "Social Media Type",
        required=True,
    )

    def action_update_post(self, access_token):

        url = (
            "https://graph.facebook.com/v15.0/%s?fields=id,caption,comments_count,is_comment_enabled,like_count,media_product_type,media_type,media_url,owner,permalink,thumbnail_url,timestamp,username&access_token=%s"
            % (self.name, access_token)
        )
        media_content = requests.get(url, timeout=5).json()
        if not media_content.get("error"):
            if media_content.get("caption"):
                self.write(
                    {
                        "caption": media_content["caption"],
                    }
                )
        else:
            raise UserError(_("%s", media_content["error"]["message"]))
