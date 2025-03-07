import base64

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class SocialMediaProfile(models.Model):
    _name = "social.media.profile"

    name = fields.Char(string="Name", readonly=True)
    access_token = fields.Char("Access Token")
    graph_api_url = fields.Char("URL")
    social_media_type = fields.Selection(
        [("instagram", "Instagram"), ("messenger", "Messenger")],
        "Social Media Type",
        required=True,
    )
    username = fields.Char("Username", readonly=True)
    account_id = fields.Char("Account ID", readonly=True)
    profile_image_url = fields.Binary(attachment=True)
    follower_count = fields.Char("Follower Count")
    user_id = fields.Many2one(comodel_name="res.users", string="User")

    def action_fetch(self):
        url = "%s/me?access_token=%s" % (self.url, self.access_token)
        page = requests.get(url)
        page_content = page.json()
        if not page_content.get("error"):
            if page_content["id"]:
                if self.social_media_type == "instagram":
                    url = "%s/%s?fields=instagram_business_account&access_token=%s" % (
                        self.url,
                        page_content["id"],
                        self.access_token,
                    )
                    business_account = requests.get(url)
                    instagram_business_account = business_account.json()[
                        "instagram_business_account"
                    ]["id"]
                    url = (
                        "%s/%s?fields=name,username,biography,website,followers_count,follows_count,media_count,profile_picture_url&access_token=%s"
                        % (self.url, instagram_business_account, self.access_token)
                    )
                    val = requests.get(url)
                    content = val.json()
                    if content.get("followers_count"):
                        self.follower_count = content["followers_count"]
                    if content.get("username"):
                        self.username = content["username"]
                    if content.get("id"):
                        self.account_id = content["id"]
                    if content.get("profile_picture_url"):
                        img = base64.b64encode(
                            requests.get(content["profile_picture_url"]).content
                        )
                        self.profile_image_url = img
                elif self.social_media_type == "messenger":
                    # url = '%s/%s?&access_token=%s' % (
                    #     self.url, page_content['id'], self.access_token)
                    # business_account = requests.get(url)
                    # instagram_business_account = business_account.json()['instagram_business_account']['id']
                    url = (
                        "%s/%s?fields=name,username,followers_count&access_token=%s"
                        % (self.url, page_content["id"], self.access_token)
                    )
                    val = requests.get(url)
                    content = val.json()
                    if content.get("name"):
                        self.name = content["name"]
                    if content.get("followers_count"):
                        self.follower_count = content["followers_count"]
                    if content.get("username"):
                        self.username = content["username"]
                    if content.get("id"):
                        self.account_id = content["id"]
                    conversations_url = (
                        "%s/%s/conversations?platform=messenger&access_token=%s"
                        % (self.url, page_content["id"], self.access_token)
                    )
                    conversations_requests = requests.get(conversations_url)
                    conversations_datas = conversations_requests.json()
                    for conversation in conversations_datas.get("data"):
                        messages_url = "%s/%s?fields=messages&access_token=%s" % (
                            self.url,
                            conversation["id"],
                            self.access_token,
                        )
                        messages_requests = requests.get(messages_url)
                        messages_datas = messages_requests.json()
                        for message in messages_datas.get("messages").get("data"):
                            to_partners_objs = False
                            from_partners_objs = False
                            users_messages_url = (
                                "%s/%s?fields=to,from,message&access_token=%s"
                                % (self.url, message["id"], self.access_token)
                            )
                            user_messages_requests = requests.get(users_messages_url)
                            user_messages_datas = user_messages_requests.json()
                            from_user_name = user_messages_datas.get("from")
                            to_user_name = user_messages_datas.get("to").get("data")[0]
                            user_message = user_messages_datas.get("message")
                            self._cr.execute(
                                """SELECT rp.id
                                FROM res_partner rp
                                WHERE rp.id_social_media = %s""",
                                [from_user_name.get("id")],
                            )
                            from_partners = self._cr.dictfetchall()
                            if not from_partners:
                                from_partners_objs = (
                                    self.env["res.partner"]
                                    .sudo()
                                    .create(
                                        [
                                            {
                                                "name": from_user_name.get("name"),
                                                "id_social_media": from_user_name.get(
                                                    "id"
                                                ),
                                                "email": from_user_name.get("email"),
                                            }
                                        ]
                                    )
                                )
                            self._cr.execute(
                                """SELECT rp.id
                                                FROM res_partner rp
                                                WHERE rp.id_social_media = %s""",
                                [to_user_name.get("id")],
                            )
                            to_partners = self._cr.dictfetchall()
                            if not to_partners:
                                to_partners_objs = (
                                    self.env["res.partner"]
                                    .sudo()
                                    .create(
                                        [
                                            {
                                                "name": to_user_name.get("name"),
                                                "id_social_media": to_user_name.get(
                                                    "id"
                                                ),
                                                "email": to_user_name.get("email"),
                                            }
                                        ]
                                    )
                                )
                            # if from_partners:
                            #     from_channel = self.get_channel(from_partners[0].get('id'), self)
                            # else:
                            #     from_channel = self.get_channel(from_partners_objs.id, self)

                            # if from_partners_objs or from_partners_objs:
                            from_channel = False
                            if (
                                self.env["res.partner"]
                                .sudo()
                                .browse(
                                    from_partners[0].get("id")
                                    if from_partners
                                    else from_partners_objs.id
                                )
                                .id_social_media
                                != self.account_id
                            ):
                                from_channel = self.get_channel(
                                    from_partners[0].get("id")
                                    if from_partners
                                    else from_partners_objs.id,
                                    self,
                                )
                            elif (
                                self.env["res.partner"]
                                .sudo()
                                .browse(
                                    to_partners[0].get("id")
                                    if to_partners
                                    else to_partners_objs.id
                                )
                                .id_social_media
                                != self.account_id
                            ):
                                from_channel = self.get_channel(
                                    to_partners[0].get("id")
                                    if to_partners
                                    else to_partners_objs.id,
                                    self,
                                )

                            social_media_message = (
                                self.env["social.media.messages"]
                                .sudo()
                                .create(
                                    {
                                        "message": user_message,
                                        "social_media_type": self.social_media_type,
                                        "from_partner_id": from_partners[0].get("id")
                                        if from_partners
                                        else from_partners_objs.id,
                                        "to_partner_id": to_partners[0].get("id")
                                        if to_partners
                                        else to_partners_objs.id,
                                    }
                                )
                            )
                            if from_channel:
                                message_values = {
                                    "body": user_message,
                                    "author_id": from_partners[0].get("id")
                                    if from_partners
                                    else from_partners_objs.id,
                                    "email_from": social_media_message.from_partner_id.email
                                    or "",
                                    "model": "discuss.channel",
                                    "message_type": "facebook_msgs",
                                    "subtype_id": self.env["ir.model.data"]
                                    .sudo()
                                    ._xmlid_to_res_id("mail.mt_comment"),
                                    # 'channel_ids': [(4, channel.id)],
                                    "partner_ids": [
                                        (
                                            4,
                                            from_partners[0].get("id")
                                            if from_partners
                                            else from_partners_objs.id,
                                        )
                                    ],
                                    "res_id": from_channel.id,
                                    "reply_to": social_media_message.to_partner_id.email,
                                }
                                message = (
                                    self.env["mail.message"]
                                    .sudo()
                                    .create(message_values)
                                )

                    # if content.get('profile_picture_url'):
                    #     img = base64.b64encode(requests.get(content['profile_picture_url']).content)
                    #     self.profile_image_url = img
        else:
            raise UserError(_("%s", page_content["error"]["message"]))

    def get_channel(self, partner_to, profile):
        partner = False
        partner = self.env["res.partner"].sudo().browse(partner_to)
        # if self.env.user.has_group('base.group_user'):
        #     partner_to.append(self.env.user.partner_id.id)
        # else:
        #     partner_to.append(profile.user_id.partner_id.id)
        channel = False

        social_media_channel_profile_line_id = (
            partner.social_media_channel_profile_line_ids.filtered(
                lambda s: s.social_media_profile_id == profile
            )
        )
        if social_media_channel_profile_line_id:
            channel = social_media_channel_profile_line_id.channel_id
            if (
                channel
                and partner_to not in channel.channel_partner_ids.ids
                and self.env.user.has_group("base.group_user")
            ):
                channel.sudo().write({"channel_partner_ids": [(4, partner_to)]})
        else:
            # phone change to mobile
            name = partner.name + partner.id_social_media
            channel = (
                self.env["discuss.channel"]
                .sudo()
                .create(
                    {
                        "channel_type": "chat",
                        "name": name,
                        "channel_partner_ids": [(4, partner_to)],
                    }
                )
            )
            channel.write(
                {
                    "channel_member_ids": [(5, 0, 0)]
                    + [(0, 0, {"partner_id": partner_to})]
                }
            )
            # partner.write({'channel_id': channel.id})
            partner.write(
                {
                    "social_media_channel_profile_line_ids": [
                        (
                            0,
                            0,
                            {
                                "channel_id": channel.id,
                                "social_media_profile_id": profile.id,
                            },
                        )
                    ]
                }
            )
        return channel

    def get_follower_data(self):
        return True

    def action_get_post(self):
        if self.social_media_type == "instagram":
            url = "https://graph.facebook.com/v15.0/%s/media?access_token=%s" % (
                self.account_id,
                self.access_token,
            )
            content = requests.get(url, timeout=5).json()
            if not content.get("error"):
                post_list = []
                # records = self.env['social.media.post'].search([])
                # for post in records:
                #     post_list.append(post.name)
                if content.get("data"):
                    for vals in content["data"]:
                        if vals["id"] not in post_list:
                            url = (
                                "https://graph.facebook.com/v14.0/%s?fields=id,caption,comments_count,is_comment_enabled,like_count,media_product_type,media_type,media_url,owner,permalink,thumbnail_url,timestamp,username&access_token=%s"
                                % (vals["id"], self.access_token)
                            )
                            media_content = requests.get(url, timeout=5).json()

                            if media_content.get("media_type"):
                                if media_content["media_type"] == "IMAGE":
                                    res = self.env["social.media.post"].create(
                                        {
                                            "name": media_content["id"],
                                            "profile_id": self.id,
                                        }
                                    )

                                    image_data = base64.b64encode(
                                        requests.get(media_content["media_url"]).content
                                    )
                                    res.write(
                                        {
                                            "post_image": image_data,
                                        }
                                    )
                                    if media_content.get("caption"):
                                        res.write(
                                            {
                                                "caption": media_content["caption"],
                                            }
                                        )

                        else:
                            record = self.env["social.media.post"].search(
                                [("name", "=", vals["id"])]
                            )
                            record.action_update_post(self.access_token)
            else:
                raise UserError(_("%s", content["error"]["message"]))
        else:
            url = "%s/%s/posts?access_token=%s" % (
                self.url,
                self.account_id,
                self.access_token,
            )
            content = requests.get(url, timeout=5).json()
            if not content.get("error"):
                post_list = []
                # records = self.env['social.media.post'].search([])
                # for post in records:
                #     post_list.append(post.name)
                if content.get("data"):
                    for vals in content["data"]:
                        if vals["id"] not in post_list:
                            url = (
                                "https://graph.facebook.com/v14.0/%s?fields=id,caption,comments_count,is_comment_enabled,like_count,media_product_type,media_type,media_url,owner,permalink,thumbnail_url,timestamp,username&access_token=%s"
                                % (vals["id"], self.access_token)
                            )
                            media_content = requests.get(url, timeout=5).json()

                            if media_content.get("media_type"):
                                if media_content["media_type"] == "IMAGE":
                                    res = self.env["social.media.post"].create(
                                        {
                                            "name": media_content["id"],
                                            "profile_id": self.id,
                                        }
                                    )

                                    image_data = base64.b64encode(
                                        requests.get(media_content["media_url"]).content
                                    )
                                    res.write(
                                        {
                                            "post_image": image_data,
                                        }
                                    )
                                    if media_content.get("caption"):
                                        res.write(
                                            {
                                                "caption": media_content["caption"],
                                            }
                                        )

                        else:
                            record = self.env["social.media.post"].search(
                                [("name", "=", vals["id"])]
                            )
                            record.action_update_post(self.access_token)
            else:
                raise UserError(_("%s", content["error"]["message"]))

    # def reload_with_get_status(self):
    #     if self.graph_api_url and self.graph_api_instance_id and self.access_token:
    #         url = self.graph_api_url + self.graph_api_instance_id + "?access_token=" + self.graph_api_token
    #
    #         payload = {
    #             'full': True,
    #         }
    #         headers = {}
    #         try:
    #             response = requests.request("GET", url, headers=headers, data=payload)
    #         except requests.exceptions.ConnectionError:
    #             raise UserError(
    #                 ("please check your internet connection."))
    #         if response.status_code == 200:
    #             dict = json.loads(response.text)
    #             # if dict['status'] == 'connected':
    #             # if dict['id'] == '111367598360060':
    #             if dict['id'] == self.graph_api_instance_id:
    #                 self.graph_api_authenticated = True
    #
    #                 IrConfigParam = request.env['ir.config_parameter'].sudo()
    #                 base_url = IrConfigParam.get_param('web.base.url', False)
    #
    #                 data = {
    #                     "webhookUrl": base_url + "/graph_tus/webhook"
    #                 }
    #                 verify_token = self.GenerateVerifyToken()
    #                 self.call_back_url = '<p>Now, You can set below details to your facebook configurations.</p><p>Call Back URL: <u><a href="%s">%s</a></u></p><p>Verify Token: <u style="color:#017e84">%s</u></p>' % (
    #                 data.get('webhookUrl'), data.get('webhookUrl'), verify_token)
    #                 self.is_token_generated = True
    #         else:
    #             self.graph_api_authenticated = False
    #             self.call_back_url = '<p>Oops, something went wrong, Kindly Double Check the above Credentials. </p>'
