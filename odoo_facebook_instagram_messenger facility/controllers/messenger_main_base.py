import base64
import json

import requests

from odoo import http
from odoo.http import request


class WebHook3(http.Controller):
    _webhook_url = "/graph_api/webhook"
    _meta_fb_url = "/graph_api/webhook"

    @http.route(_webhook_url, type="http", methods=["GET"], auth="public", csrf=False)
    def facebook_webhook(self, **kw):
        if kw.get("hub.verify_token"):
            return kw.get("hub.challenge")

    # def get_channel(self, partner_to, provider):
    #     partner = False
    #     if len(partner_to) > 0:
    #         partner = request.env['res.partner'].sudo().browse(partner_to[0])
    #     if request.env.user.has_group('base.group_user'):
    #         partner_to.append(request.env.user.partner_id.id)
    #     else:
    #         partner_to.append(provider.user_id.partner_id.id)
    #     channel = False
    #
    #     provider_channel_id = partner.messenger_channel_provider_line_ids.filtered(lambda s: s.provider_id == provider)
    #     if provider_channel_id:
    #         channel = provider_channel_id.channel_id
    #         if request.env.user.partner_id.id not in channel.channel_partner_ids.ids and request.env.user.has_group(
    #                 'base.group_user'):
    #             channel.sudo().write({'messenger_channel_provider_line_ids': [(4, request.env.user.partner_id.id)]})
    #     else:
    #         # phone change to mobile
    #         if partner.messenger_account_id:
    #             name = partner.messenger_account_id
    #             channel = request.env['mail.channel'].sudo().create({
    #                 # 'public': 'public',
    #                 'channel_type': 'chat',
    #                 'name': name,
    #                 'facebook_channel': True,
    #                 'channel_partner_ids': [(4, x) for x in partner_to],
    #             })
    #             # channel.write({'channel_member_ids': [(5, 0, 0)] + [
    #             #     (0, 0, {'partner_id': line_vals}) for line_vals in partner_to]})
    #             # partner.write({'channel_id': channel.id})
    #             partner.write({'messenger_channel_provider_line_ids': [
    #                 (0, 0, {'channel_id': channel.id, 'messenger_provider_id': provider.id})]})
    #         elif partner.instagram_account_id:
    #             name = partner.instagram_account_id
    #             channel = request.env['mail.channel'].sudo().create({
    #                 # 'public': 'public',
    #                 'channel_type': 'chat',
    #                 'name': name,
    #                 'instagram_channel': True,
    #                 'channel_partner_ids': [(4, x) for x in partner_to],
    #             })
    #             # channel.write({'channel_member_ids': [(5, 0, 0)] + [
    #             #     (0, 0, {'partner_id': line_vals}) for line_vals in partner_to]})
    #             # partner.write({'channel_id': channel.id})
    #             partner.write({'messenger_channel_provider_line_ids': [
    #                 (0, 0, {'channel_id': channel.id, 'messenger_provider_id': provider.id})]})
    #     return channel

    # def get_url(self, provider, media_id, social_media_id):
    #     if provider.graph_api_authenticated:
    #         url = provider.graph_api_url + media_id + "?id=" + social_media_id + "&access_token=" + provider.graph_api_token
    #         headers = {'Content-type': 'application/json'}
    #         payload = {}
    #         try:
    #             answer = requests.request("GET", url, headers=headers, data=payload)
    #         except requests.exceptions.ConnectionError:
    #             raise UserError(
    #                 ("please check your internet connection."))
    #         return answer
    #     else:
    #         raise UserError(
    #             ("please authenticated your messenger."))

    #
    def get_media_data(self, url, provider):
        payload = {}
        headers = {"Authorization": "Bearer " + provider.graph_api_token}
        response = requests.request("GET", url, headers=headers, data=payload)
        decoded = base64.b64encode(response.content)
        return decoded

    @http.route(
        _meta_fb_url, type="json", methods=["GET", "POST"], auth="public", csrf=False
    )
    def messenger_meta_webhook(self, **kw):
        wa_dict = {}
        data = json.loads(request.httprequest.data.decode("utf-8"))
        wa_dict.update({"messages": data.get("messages")})

        provider = (
            request.env["messenger.provider"]
            .sudo()
            .search([("graph_api_authenticated", "=", True)], limit=1)
        )
        wa_dict.update({"provider": provider})
        data_obj = data.get("object")

        if provider.graph_api_authenticated:
            user_partner = provider.user_id.partner_id
            if data and data.get("entry"):
                if data.get("entry")[0].get("messaging"):
                    if data.get("entry")[0].get("messaging")[0].get("message"):
                        if data.get("entry")[0].get("messaging")[0].get("message"):
                            page_id = (
                                data.get("entry")[0]
                                .get("messaging")[0]
                                .get("sender")
                                .get("id")
                            )
                            messages_id = (
                                data.get("entry")[0]
                                .get("messaging")[0]
                                .get("message")
                                .get("mid")
                            )
                            #                             # messages_body = mes.get('text').get('body')
                            wa_dict.update({"chat": True})
                            partners = False
                            if data_obj == "page":
                                partners = (
                                    request.env["res.partner"]
                                    .sudo()
                                    .search([("messenger_account_id", "=", page_id)])
                                )
                                wa_dict.update({"partners": partners})
                                if not partners:
                                    user_conversation_url = (
                                        "%s/%s/conversations?platform=messenger&user_id=%s&access_token=%s"
                                        % (
                                            provider.graph_api_url,
                                            provider.account_id,
                                            page_id,
                                            provider.graph_api_token,
                                        )
                                    )

                                    user_conversations_requests = requests.get(
                                        user_conversation_url
                                    )
                                    user_conversations_datas = (
                                        user_conversations_requests.json()
                                    )
                                    if user_conversations_datas.get("data"):
                                        messages_url = (
                                            "%s/%s?fields=messages&access_token=%s"
                                            % (
                                                provider.graph_api_url,
                                                user_conversations_datas.get("data")[
                                                    0
                                                ].get("id"),
                                                provider.graph_api_token,
                                            )
                                        )
                                        messages_requests = requests.get(messages_url)
                                        messages_datas = messages_requests.json()
                                        if messages_datas.get("messages").get("data"):
                                            users_messages_url = (
                                                "%s/%s?fields=to,from,message&access_token=%s"
                                                % (
                                                    provider.graph_api_url,
                                                    messages_datas.get("messages")
                                                    .get("data")[0]
                                                    .get("id"),
                                                    provider.graph_api_token,
                                                )
                                            )
                                            user_messages_requests = requests.get(
                                                users_messages_url
                                            )
                                            user_messages_datas = (
                                                user_messages_requests.json()
                                            )
                                            user_user_name = user_messages_datas.get(
                                                "from"
                                            )

                                            partners = (
                                                request.env["res.partner"]
                                                .sudo()
                                                .create(
                                                    {
                                                        "name": user_user_name.get(
                                                            "name"
                                                        ),
                                                        "messenger_account_id": page_id,
                                                        "email": user_user_name.get(
                                                            "email"
                                                        ),
                                                    }
                                                )
                                            )

                            elif data_obj == "instagram":
                                partners = (
                                    request.env["res.partner"]
                                    .sudo()
                                    .search([("instagram_account_id", "=", page_id)])
                                )
                                wa_dict.update({"partners": partners})
                                if not partners:
                                    user_conversation_url = (
                                        "%s/%s/conversations?platform=instagram&user_id=%s&access_token=%s"
                                        % (
                                            provider.graph_api_url,
                                            provider.account_id,
                                            page_id,
                                            provider.graph_api_token,
                                        )
                                    )

                                    user_conversations_requests = requests.get(
                                        user_conversation_url
                                    )
                                    user_conversations_datas = (
                                        user_conversations_requests.json()
                                    )
                                    if user_conversations_datas.get("data"):
                                        messages_url = (
                                            "%s/%s?fields=messages&access_token=%s"
                                            % (
                                                provider.graph_api_url,
                                                user_conversations_datas.get("data")[
                                                    0
                                                ].get("id"),
                                                provider.graph_api_token,
                                            )
                                        )
                                        messages_requests = requests.get(messages_url)
                                        messages_datas = messages_requests.json()
                                        if messages_datas.get("messages").get("data"):
                                            users_messages_url = (
                                                "%s/%s?fields=to,from,message&access_token=%s"
                                                % (
                                                    provider.graph_api_url,
                                                    messages_datas.get("messages")
                                                    .get("data")[0]
                                                    .get("id"),
                                                    provider.graph_api_token,
                                                )
                                            )
                                            user_messages_requests = requests.get(
                                                users_messages_url
                                            )
                                            user_messages_datas = (
                                                user_messages_requests.json()
                                            )
                                            user_user_name = user_messages_datas.get(
                                                "from"
                                            )

                                            partners = (
                                                request.env["res.partner"]
                                                .sudo()
                                                .create(
                                                    {
                                                        "name": user_user_name.get(
                                                            "username"
                                                        ),
                                                        "instagram_account_id": page_id,
                                                        "email": user_user_name.get(
                                                            "email"
                                                        ),
                                                    }
                                                )
                                            )

                            for partner in partners:
                                partner_id = partner.id
                                message = (
                                    data.get("entry")[0]
                                    .get("messaging")[0]
                                    .get("message")
                                )
                                # channel = self.get_channel([int(partner_id)], provider)
                                if message.get("text"):
                                    vals = {
                                        "provider_id": provider.id,
                                        "author_id": user_partner.id,
                                        "message": data.get("entry")[0]
                                        .get("messaging")[0]
                                        .get("message")
                                        .get("text"),
                                        "message_id": messages_id,
                                        "type": "received",
                                        "partner_id": partner_id,
                                        "account_id": page_id,
                                        "attachment_ids": False,
                                        "company_id": provider.company_id.id,
                                        # 'date':datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                    }
                                    if data_obj == "page":
                                        if "context" in data.get("entry")[0].get(
                                            "messaging"
                                        )[0].get("message"):
                                            request.env[
                                                "messenger.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": data.get("entry")[0]
                                                    .get("messaging")[0]
                                                    .get("message")
                                                    .get("context")
                                                    .get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().create(vals)
                                    elif data_obj == "instagram":
                                        if "context" in data.get("entry")[0].get(
                                            "messaging"
                                        )[0].get("message"):
                                            request.env[
                                                "instagram.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": data.get("entry")[0]
                                                    .get("messaging")[0]
                                                    .get("message")
                                                    .get("context")
                                                    .get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().create(vals)

                                elif (
                                    message.get("attachments")[0].get("type") == "image"
                                ):
                                    media_url = (
                                        message.get("attachments")[0]
                                        .get("payload")
                                        .get("url")
                                    )
                                    decoded = self.get_media_data(media_url, provider)

                                    attachment_value = {
                                        "name": "messenger_image",
                                        "datas": decoded,
                                        "type": "binary",
                                        "mimetype": "image/jpeg",
                                    }
                                    attachment = (
                                        request.env["ir.attachment"]
                                        .sudo()
                                        .create(attachment_value)
                                    )
                                    if "context" in message:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }

                                    else:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }
                                    if data_obj == "page":
                                        if "context" in message:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().create(vals)
                                    elif data_obj == "instagram":
                                        if "context" in message:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().create(vals)

                                elif (
                                    message.get("attachments")[0].get("type") == "video"
                                ):
                                    media_url = (
                                        message.get("attachments")[0]
                                        .get("payload")
                                        .get("url")
                                    )
                                    decoded = self.get_media_data(media_url, provider)

                                    attachment_value = {
                                        "name": "messenger_video",
                                        "datas": decoded,
                                        "type": "binary",
                                        "mimetype": "video/mp4",
                                    }
                                    attachment = (
                                        request.env["ir.attachment"]
                                        .sudo()
                                        .create(attachment_value)
                                    )
                                    if "context" in message:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }

                                    else:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }
                                    if data_obj == "page":
                                        if "context" in message:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().create(vals)
                                    elif data_obj == "instagram":
                                        if "context" in message:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().create(vals)

                                elif (
                                    message.get("attachments")[0].get("type") == "file"
                                ):
                                    media_url = (
                                        message.get("attachments")[0]
                                        .get("payload")
                                        .get("url")
                                    )
                                    decoded = self.get_media_data(media_url, provider)

                                    attachment_value = {
                                        "name": "messenger_file",
                                        "datas": decoded,
                                        "type": "binary",
                                        "mimetype": "application/pdf",
                                    }
                                    attachment = (
                                        request.env["ir.attachment"]
                                        .sudo()
                                        .create(attachment_value)
                                    )
                                    if "context" in message:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }

                                    else:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }
                                    if data_obj == "page":
                                        if "context" in message:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().create(vals)
                                    elif data_obj == "instagram":
                                        if "context" in message:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().create(vals)

                                elif (
                                    message.get("attachments")[0].get("type") == "audio"
                                ):
                                    media_url = (
                                        message.get("attachments")[0]
                                        .get("payload")
                                        .get("url")
                                    )
                                    decoded = self.get_media_data(media_url, provider)

                                    attachment_value = {
                                        "name": "messenger_audio",
                                        "datas": decoded,
                                        "type": "binary",
                                        "mimetype": "audio/mpeg",
                                    }
                                    attachment = (
                                        request.env["ir.attachment"]
                                        .sudo()
                                        .create(attachment_value)
                                    )
                                    if "context" in message:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }

                                    else:
                                        vals = {
                                            "message_id": messages_id,
                                            "author_id": user_partner.id,
                                            "type": "received",
                                            "partner_id": partner_id,
                                            "account_id": page_id,
                                            "attachment_ids": [(4, attachment.id)],
                                            "provider_id": provider.id,
                                            "company_id": provider.company_id.id,
                                            # 'date': datetime.datetime.fromtimestamp(int(mes.get('time'))),
                                        }
                                    if data_obj == "page":
                                        if "context" in message:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "messenger.history"
                                            ].sudo().create(vals)
                                    elif data_obj == "instagram":
                                        if "context" in message:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().with_context(
                                                {
                                                    "quotedMsgId": message.get(
                                                        "context"
                                                    ).get("id")
                                                }
                                            ).create(
                                                vals
                                            )
                                        else:
                                            request.env[
                                                "instagram.history"
                                            ].sudo().create(vals)

        return wa_dict


# @http.route(['/send/product'], type='json', methods=['POST'])
# def _send_product_by_whatsapp(self, **kw):
#     provider_id = False
#     if 'provider_id' in kw and kw.get('provider_id') != '':
#         channel_company_line_id = request.env['channel.provider.line'].search(
#             [('channel_id', '=', kw.get('provider_id'))])
#         if channel_company_line_id.provider_id:
#             provider_id = channel_company_line_id.provider_id
#
#     # image = kw.get('image').split(',')[1]
#     Attachment = request.env['ir.attachment']
#     partner_id = request.env['res.partner'].sudo().browse(int(kw.get('partner_id')))
#     product = request.env['product.product'].sudo().browse(int(kw.get('product_id')))
#     body_message = product.name + "\n" + request.env.user.company_id.currency_id.symbol + " " + str(
#         product.list_price) + " / " + product.uom_id.name
#     attac_id = False
#     if product.image_1920:
#         name = product.name + '.png'
#         attac_id = request.env['ir.attachment'].sudo().search([('name', '=', name)], limit=1)
#         if not attac_id:
#             attac_id = Attachment.create({'name': name,
#                                           'type': 'binary',
#                                           'datas': product.image_1920,
#                                           'store_fname': name,
#                                           'res_model': 'wa.msgs',
#                                           'mimetype': 'image/jpeg',
#                                           })
#     user_partner = request.env.user.partner_id
#     channel = self.get_channel([int(kw.get('partner_id'))], provider_id)
#
#     if channel:
#         message_values = {
#             'body': body_message,
#             'author_id': user_partner.id,
#             'email_from': user_partner.email or '',
#             'model': 'mail.channel',
#             'message_type': 'wa_msgs',
#             'isWaMsgs': True,
#             # 'subtype_id': request.env['ir.model.data'].sudo().xmlid_to_res_id('mail.mt_comment'),
#             'subtype_id': request.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_comment'),
#             # 'channel_ids': [(4, channel.id)],
#             'partner_ids': [(4, user_partner.id)],
#             'res_id': channel.id,
#             'reply_to': user_partner.email,
#             # 'company_id': kw.get('company_id'),
#         }
#         if attac_id:
#             message_values.update({'attachment_ids': [(4, attac_id.id)]})
#         message = request.env['mail.message'].sudo().with_context({'provider_id': provider_id}).create(
#             message_values)
#         notifications = channel._channel_message_notifications(message)
#         request.env['bus.bus']._sendmany(notifications)
#
#     return True

# @http.route(['/send/pre/message'], type='json', methods=['POST'])
# def _send_pre_message_by_whatsapp(self, **kw):
#     template_id = request.env['wa.template'].sudo().browse(int(kw.get('template_id')))
#     active_model = template_id.model
#     provider_id = template_id.provider_id
#     wizard_rec = request.env['wa.compose.message'].with_context(active_model=active_model,
#                                                                 active_id=int(kw.get('partner_id'))).create(
#         {'partner_id': int(kw.get('partner_id')), 'provider_id': provider_id.id,
#          'template_id': int(kw.get('template_id'))})
#     wizard_rec.onchange_template_id_wrapper()
#     return wizard_rec.send_whatsapp_message()

# if data and data.get('entry'):
#     if data.get('entry')[0].get('messaging'):
#         if data.get('entry')[0].get('messaging')[0].get('message'):
#             for acknowledgment in data.get('entry')[0].get('messaging'):
#                 wp_msgs = request.env['messenger.history'].sudo().search(
#                     [('message_id', '=', acknowledgment[0].get('message').get('mid'))], limit=1)
#                 if wp_msgs:
#                     partner = request.env['res.partner'].sudo().search(
#                         ['|',
#                          ('social_media_ids.messenger_account_id', '=', acknowledgment[0].get('sender').get('id')),
#                          ('social_media_ids.instagram_account_id', '=', acknowledgment[0].get('sender').get('id'))],
#                         limit=1)
#
#                     channel = self.get_channel([int(partner.id)], provider)
#                     wa_mail_message = request.env['mail.message'].sudo().search(
#                         [('wa_message_id', '=', acknowledgment[0].get('message').get('mid'))], limit=1)
#
# if wp_msgs:
#     if acknowledgment.get('status') == 'sent':
#         wp_msgs.sudo().write({'type': 'sent'})
#     elif acknowledgment.get('status') == 'delivered':
#         wp_msgs.sudo().write({'type': 'delivered'})
#     elif acknowledgment.get('status') == 'read':
#         wp_msgs.sudo().write({'type': 'read'})
#     elif acknowledgment.get('status') == 'failed':
#         wp_msgs.sudo().write(
#             {'type': 'fail',
#              'fail_reason': acknowledgment.get('errors')[0].get('title')})
#
#         if wa_mail_message:
#             if acknowledgment.get('status') == 'sent':
#                 wa_mail_message.write({'wp_status': acknowledgment.get('status')})
#                 notifications = channel._channel_message_notifications(wa_mail_message)
#                 request.env['bus.bus']._sendmany(notifications)
#             elif acknowledgment.get('status') == 'delivered':
#                 wa_mail_message.write({'wp_status': acknowledgment.get('status')})
#                 notifications = channel._channel_message_notifications(wa_mail_message)
#                 request.env['bus.bus']._sendmany(notifications)
#             elif acknowledgment.get('status') == 'read':
#                 wa_mail_message.write({'wp_status': acknowledgment.get('status')})
#                 notifications = channel._channel_message_notifications(wa_mail_message)
#                 request.env['bus.bus']._sendmany(notifications)
#
#             elif acknowledgment.get('status') == 'failed':
#                 wa_mail_message.write(
#                     {'wp_status': 'fail', 'wa_delivery_status': acknowledgment.get('status'),
#                      'wa_error_message': acknowledgment.get('errors')[0].get(
#                          'error_data').get('details')})
#                 notifications = channel._channel_message_notifications(wa_mail_message)
#                 request.env['bus.bus']._sendmany(notifications)
