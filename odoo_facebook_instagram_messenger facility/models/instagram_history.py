import json

from odoo import api, fields, models
from odoo.exceptions import UserError

image_type = [
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/vnd.microsoft.icon",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
]
document_type = [
    "application/xhtml+xml",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/xml",
    "application/vnd.mozilla.xul+xml",
    "application/zip",
    "application/x-7z-compressed",
    "application/x-abiword",
    "application/x-freearc",
    "application/vnd.amazon.ebook",
    "application/octet-stream",
    "application/x-bzip",
    "application/x-bzip2",
    "application/x-cdf",
    "application/x-csh",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-fontobject",
    "application/epub+zip",
    "application/gzip",
    "application/java-archive",
    "application/json",
    "application/ld+json",
    "application/vnd.apple.installer+xml",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/ogg",
    "application/pdf",
    "application/x-httpd-php",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.rar",
    "application/rtf",
    "application/x-sh",
    "application/x-tar",
    "application/vnd.visio",
]
audio_type = [
    "audio/aac",
    "audio/midi",
    "audio/x-midi",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/webm",
    "audio/3gpp",
    "audio/3gpp2",
]
video_type = [
    "video/x-msvideo",
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/mp2t",
    "video/webm",
    "video/3gpp",
    "video/3gpp2",
]


class InstagramHistory(models.Model):
    _name = "instagram.history"
    _description = "Instagram Message History"

    provider_id = fields.Many2one("messenger.provider", "Provider", readonly=True)
    author_id = fields.Many2one("res.partner", "Author", readonly=True)
    partner_id = fields.Many2one("res.partner", "Recipient", readonly=True)
    account_id = fields.Char("Instagram ID")
    message = fields.Char("Message", readonly=True)
    type = fields.Selection(
        [
            ("in queue", "In queue"),
            ("sent", "Sent"),
            ("delivered", "delivered"),
            ("received", "Received"),
            ("read", "Read"),
            ("fail", "Fail"),
        ],
        string="Type",
        default="in queue",
        readonly=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Attachments", readonly=True
    )
    message_id = fields.Char("Message ID", readonly=True)
    fail_reason = fields.Char("Fail Reason", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )
    date = fields.Datetime("Date", default=fields.Datetime.now, readonly=True)
    model = fields.Char("Related Document Model", index=True, readonly=True)
    active = fields.Boolean("Active", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            res = super(InstagramHistory, self).create(vals)

            if (
                res.provider_id
                and res.partner_id
                and res.partner_id.instagram_account_id
            ):
                # res.partner_id.write({'mobile': res.partner_id.mobile.strip('+').replace(' ', '')})
                part_lst = []
                part_lst.append(res.partner_id.id)
                if res.partner_id.id != vals.get("author_id"):
                    part_lst.append(int(vals.get("author_id")))
                channel = False
                if res.type == "received":
                    provider_channel_id = (
                        res.partner_id.messenger_channel_provider_line_ids.filtered(
                            lambda s: s.messenger_provider_id == res.provider_id
                        )
                    )
                    if provider_channel_id:
                        channel = provider_channel_id.channel_id
                    else:
                        name = res.partner_id.instagram_account_id
                        channel = self.env["discuss.channel"].create(
                            {
                                # 'public': 'public',
                                "channel_type": "chat",
                                "name": name,
                                "instagram_channel": True,
                                "channel_partner_ids": [
                                    (4, int(vals.get("partner_id")))
                                ],
                            }
                        )
                        mail_channel_partner = (
                            self.env["discuss.channel.member"]
                            .sudo()
                            .search(
                                [
                                    ("channel_id", "=", channel.id),
                                    ("partner_id", "=", int(vals.get("partner_id"))),
                                ]
                            )
                        )
                        mail_channel_partner.write({"is_pinned": True})
                        channel.write(
                            {
                                "channel_member_ids": [(5, 0, 0)]
                                + [
                                    (0, 0, {"partner_id": line_vals})
                                    for line_vals in part_lst
                                ]
                            }
                        )

                        # channel.write({'channel_member_ids': [(5, 0, 0)] + [(0, 0, {'partner_id': line_vals}) for
                        # line_vals in part_lst]})
                        res.partner_id.write(
                            {
                                "messenger_channel_provider_line_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "channel_id": channel.id,
                                            "messenger_provider_id": res.provider_id.id,
                                        },
                                    )
                                ]
                            }
                        )

                    if channel:
                        message_values = {
                            "body": res.message or "",
                            "author_id": res.partner_id.id,
                            "email_from": res.partner_id.email or "",
                            "model": "discuss.channel",
                            "message_type": "insta_msgs",
                            "message_id": vals.get("message_id"),
                            "subtype_id": self.env["ir.model.data"]
                            .sudo()
                            ._xmlid_to_res_id("mail.mt_comment"),
                            "partner_ids": [(4, res.partner_id.id)],
                            "res_id": channel.id,
                            "reply_to": res.partner_id.email,
                            # 'company_id': res.company_id.id,
                        }
                        if res.attachment_ids:
                            message_values.update(
                                {"attachment_ids": res.attachment_ids}
                            )
                        if "quotedMsgId" in self.env.context:
                            parent_message = (
                                self.env["mail.message"]
                                .sudo()
                                .search_read(
                                    [
                                        (
                                            "wa_message_id",
                                            "=",
                                            self.env.context["quotedMsgId"],
                                        )
                                    ],
                                    [
                                        "id",
                                        "body",
                                        "chatter_wa_model",
                                        "chatter_wa_res_id",
                                        "chatter_wa_message_id",
                                    ],
                                )
                            )
                            if len(parent_message) > 0:
                                message_values.update(
                                    {"parent_id": parent_message[0]["id"]}
                                )
                                if (
                                    parent_message[0].get("chatter_wa_model")
                                    and parent_message[0].get("chatter_wa_res_id")
                                    and parent_message[0].get("chatter_wa_message_id")
                                ):
                                    chatter_wa_message_values = {
                                        "body": res.message,
                                        "author_id": res.partner_id.id,
                                        "email_from": res.partner_id.email or "",
                                        "model": parent_message[0].get(
                                            "chatter_wa_model"
                                        ),
                                        "message_type": "comment",
                                        # 'isWaMsgs': True,
                                        "subtype_id": self.env["ir.model.data"]
                                        .sudo()
                                        ._xmlid_to_res_id("mail.mt_comment"),
                                        # 'channel_ids': [(4, channel.id)],
                                        "partner_ids": [(4, res.partner_id.id)],
                                        "res_id": parent_message[0].get(
                                            "chatter_wa_res_id"
                                        ),
                                        "reply_to": res.partner_id.email,
                                        "parent_id": parent_message[0].get(
                                            "chatter_wa_message_id"
                                        ),
                                    }
                                    if vals.get("attachment_ids"):
                                        message_values.update(
                                            {"attachment_ids": res.attachment_ids}
                                        )
                                    chatter_wa_message = (
                                        self.env["mail.message"]
                                        .sudo()
                                        .create(chatter_wa_message_values)
                                    )
                                    # notifications = (
                                    #     channel._channel_message_notifications(
                                    #         chatter_wa_message
                                    #     )
                                    # )
                                    notifications = [(channel, 'discuss.channel/new_message',
                                                      {'id': channel.id, 'message': chatter_wa_message_values})]
                                    self.env["bus.bus"]._sendmany(notifications)

                        message = (
                            self.env["mail.message"]
                            .sudo()
                            .with_context({"message": "received"})
                            .create(message_values)
                        )
                        # notifications = channel._channel_message_notifications(message)
                        notifications = [(channel, 'discuss.channel/new_message',
                                          {'id': channel.id, 'message': message_values})]
                        self.env["bus.bus"]._sendmany(notifications)

                else:
                    if not self.env.context.get("whatsapp_application"):
                        if res.message:
                            answer = False
                            if "message_parent_id" in self.env.context:
                                parent_msg = (
                                    self.env["mail.message"]
                                    .sudo()
                                    .search(
                                        [
                                            (
                                                "id",
                                                "=",
                                                self.env.context.get(
                                                    "message_parent_id"
                                                ).id,
                                            )
                                        ]
                                    )
                                )
                                answer = res.provider_id.instagram_send_message(
                                    res.partner_id,
                                    res.message,
                                    parent_msg.wa_message_id,
                                )
                            else:
                                answer = res.provider_id.instagram_send_message(
                                    res.partner_id, res.message
                                )
                            if answer.status_code == 200:
                                dict = json.loads(answer.text)
                                if (
                                    res.provider_id.provider == "graph_api"
                                ):  # if condition for Graph API
                                    if (
                                        "messages" in dict
                                        and dict.get("messages")
                                        and dict.get("messages")[0].get("id")
                                    ):
                                        res.message_id = dict.get("messages")[0].get(
                                            "id"
                                        )
                                        if self.env.context.get("wa_messsage_id"):
                                            self.env.context.get(
                                                "wa_messsage_id"
                                            ).wa_message_id = dict.get("messages")[
                                                0
                                            ].get(
                                                "id"
                                            )

                                else:
                                    if "sent" in dict and dict.get("sent"):
                                        res.message_id = dict["id"]
                                        if self.env.context.get("wa_messsage_id"):
                                            self.env.context.get(
                                                "wa_messsage_id"
                                            ).wa_message_id = dict["id"]
                                    else:
                                        if not self.env.context.get("cron"):
                                            if "message" in dict:
                                                raise UserError(dict.get("message"))
                                            if "error" in dict:
                                                raise UserError(
                                                    dict.get("error").get("message")
                                                )
                                        else:
                                            res.write({"type": "fail"})
                                            if "message" in dict:
                                                res.write(
                                                    {"fail_reason": dict.get("message")}
                                                )

                        if res.attachment_ids:
                            for attachment_id in res.attachment_ids:
                                if res.provider_id.provider == "chat_api":
                                    answer = res.provider_id.send_file(
                                        res.partner_id, attachment_id
                                    )
                                    if answer.status_code == 200:
                                        dict = json.loads(answer.text)
                                        if "sent" in dict and dict.get("sent"):
                                            res.message_id = dict["id"]
                                            if self.env.context.get("wa_messsage_id"):
                                                self.env.context.get(
                                                    "wa_messsage_id"
                                                ).wa_message_id = dict["id"]
                                        else:
                                            if not self.env.context.get("cron"):
                                                if "message" in dict:
                                                    raise UserError(
                                                        dict.get("message")
                                                    )
                                                if "error" in dict:
                                                    raise UserError(
                                                            dict.get("error").get(
                                                                "message"
                                                            )
                                                    )
                                            else:
                                                res.write({"type": "fail"})
                                                if "message" in dict:
                                                    res.write(
                                                        {
                                                            "fail_reason": dict.get(
                                                                "message"
                                                            )
                                                        }
                                                    )

                                if res.provider_id.provider == "graph_api":
                                    sent_type = False
                                    IrConfigParam = self.env[
                                        "ir.config_parameter"
                                    ].sudo()
                                    base_url = IrConfigParam.get_param(
                                        "web.base.url", False
                                    )
                                    if attachment_id.mimetype in image_type:
                                        sent_type = "image"
                                        media_url = (
                                            base_url
                                            + "/web/image/"
                                            + str(res.attachment_ids.ids[0])
                                            + "/datas"
                                        )
                                    elif attachment_id.mimetype in document_type:
                                        sent_type = "document"
                                        media_url = {
                                            "link": base_url
                                            + "/web/content/"
                                            + str(res.attachment_ids.ids[0]),
                                            "filename": self.env["ir.attachment"]
                                            .sudo()
                                            .browse(res.attachment_ids.ids[0])
                                            .name,
                                        }
                                    elif attachment_id.mimetype in audio_type:
                                        sent_type = "audio"
                                        media_url = (
                                            base_url
                                            + "/web/content/"
                                            + str(res.attachment_ids[0].id)
                                        )
                                    elif attachment_id.mimetype in video_type:
                                        sent_type = "video"
                                        media_url = (
                                            base_url
                                            + "/web/content/"
                                            + str(res.attachment_ids.ids[0])
                                        )
                                    else:
                                        sent_type = "image"
                                        media_url = (
                                            base_url
                                            + "/web/image/"
                                            + str(res.attachment_ids[0].id)
                                            + "/datas"
                                        )

                                    answer = res.provider_id.instagram_send_media(
                                        media_url,
                                        res.partner_id,
                                        sent_type,
                                        attachment_id,
                                    )
                                    if answer.status_code == 200:
                                        imagedict = json.loads(answer.text)
                                        if "messages" in imagedict and imagedict.get(
                                            "messages"
                                        ):
                                            res.message_id = imagedict.get("id")
                                            if self.env.context.get("wa_messsage_id"):
                                                self.env.context.get(
                                                    "wa_messsage_id"
                                                ).wa_message_id = imagedict.get("id")
                                        else:
                                            if not self.env.context.get("cron"):
                                                if "messages" in imagedict:
                                                    raise UserError(
                                                        imagedict.get("message")
                                                    )
                                                if "error" in imagedict:
                                                    raise UserError(
                                                            imagedict.get("error").get(
                                                                "message"
                                                            )
                                                    )
                                            else:
                                                res.write({"type": "fail"})
                                                if "messages" in imagedict:
                                                    res.write(
                                                        {
                                                            "fail_reason": imagedict.get(
                                                                "message"
                                                            )
                                                        }
                                                    )
            return res
