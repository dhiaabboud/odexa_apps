# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
import requests
import base64
import json
import yaml
from datetime import datetime


class SlackAuthorization(http.Controller):
    @http.route('/slack_token/', auth='public')
    def authorization(self, **kw):
        try:
            if 'code' in kw:
                IrConfigParameter = request.env['ir.config_parameter'].sudo()
                client_id = IrConfigParameter.get_param('odoo_slack.sl_client_id')
                client_secret = IrConfigParameter.get_param('odoo_slack.sl_client_secret')

                headers = {
                    'Content-Type': "application/x-www-form-urlencoded"
                }
                url = "https://slack.com/api/oauth.v2.access"
                payload = {
                    "code": kw['code'],
                    "client_id": client_id,
                    "client_secret": client_secret
                }
                response = requests.request("POST", url, data=payload, headers=headers)
                if 'authed_user' in json.loads(response.text):
                    access_token = json.loads(response.text)['authed_user']['access_token']
                    request.env['ir.config_parameter'].sudo().set_param('odoo_slack.access_token', access_token)
                    return request.render("slack_odoo_connector.token_redirect_success_page")
                else:
                    return request.render("slack_odoo_connector.token_redirect_fail_page")
            else:
                return request.render("slack_odoo_connector.token_redirect_fail_page")
        except Exception as e:
            raise ValidationError(str(e))

    @http.route('/event/', auth='public',type='json')
    def event(self, **kw):
        try:
            data = request.httprequest.data
            data_in_json = yaml.safe_load(data)
            if 'challenge' in data_in_json:
                challenge = data_in_json['challenge']
                if challenge:
                    return challenge
            else:
                mail_message=[]
                token = request.env['ir.config_parameter'].sudo().get_param('odoo_slack.access_token')
                user = request.env['res.users'].sudo().search(
                    [('sl_slack_user_id', '=', data_in_json['event']['user'])])
                recipient_partner = user.commercial_partner_id.id
                ts = float(data_in_json['event']['ts'])
                date_time = datetime.fromtimestamp(ts)
                channel = request.env['discuss.channel'].sudo().search(
                    [('sl_slack_channel_id', '=', data_in_json['event']['channel'])])
                odoo_message = request.env['mail.message'].sudo().search(
                    [('client_message_id', '=', data_in_json['event']['client_msg_id'])])
                if not odoo_message:
                    if 'files' in data_in_json['event']:
                        slack_attachment_ids = []
                        for file in data_in_json['event']['files']:
                            file_redundency_check = request.env['ir.attachment'].sudo().search([('sl_attachment_id', '=', file['id'])])
                            if file_redundency_check:
                                slack_attachment_ids.append(file_redundency_check.id)
                            else:
                                url = file['url_private']
                                response = requests.get(url=url, headers={
                                    'Accept': 'application/json',
                                    'Authorization': 'Bearer ' + token
                                })
                                msg = base64.b64encode(response.content)
                                attachment_id = request.env['ir.attachment'].sudo().create({
                                    'name': file['name'],
                                    'res_model': 'mail.message',
                                    'datas': msg,
                                    'sl_attachment_id': file['id']
                                })
                                request.env.cr.commit()
                                slack_attachment_ids.append(attachment_id.id)
                        ts = float(data_in_json['event']['ts'])
                        date_time = datetime.fromtimestamp(ts)
                        message_creator = request.env['res.users'].sudo().search([('sl_slack_user_id', '=', data_in_json['event']['user'])])
                        mail_message .append((0,0,{
                            'subject': data_in_json['event']['text'],
                            'attachment_ids' : [[6,0,slack_attachment_ids]],
                            'date': date_time,
                            'message_type': 'comment',
                            'model': 'discuss.channel',
                            'body': data_in_json['event']['text'],
                            'client_message_id': data_in_json['event']['client_msg_id'],
                            'email_from': message_creator.email,
                            'author_id': message_creator.partner_id.id,
                        }))
                        request.env.cr.commit()
                    else:
                        mail_message .append((0,0,{
                            'subject': data_in_json['event']['text'],
                            'date': date_time,
                            'body': data_in_json['event']['text'],
                            'client_message_id': data_in_json['event']['client_msg_id'],
                            'message_type': 'comment',
                            'model': 'discuss.channel',
                            'res_id': recipient_partner,
                            'author_id': recipient_partner
                        }))
                if channel:
                    channel.write({
                        'message_ids': mail_message,
                    })
                    request.env.cr.commit()
                    return 200
                else:
                    return 200
        except Exception as e:
            raise ValidationError(str(e))

