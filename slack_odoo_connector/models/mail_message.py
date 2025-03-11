# -*- coding: utf-8 -*-
from odoo import models, fields, api
from slack import WebClient
import base64
from odoo.exceptions import ValidationError
class MailMessage(models.Model):
    _inherit = 'mail.message'

    client_message_id = fields.Char('Client Message Id')

    @api.model_create_multi
    def create(self, vals_list):
        try:
            for values in vals_list:
                IrConfigParameter = self.env['ir.config_parameter'].sudo()
                is_slack = IrConfigParameter.get_param('odoo_slack.sl_is_slack')
                if is_slack == 'True':
                    token = IrConfigParameter.get_param('odoo_slack.access_token')
                    sc = WebClient(token)
                    if values['body'] == 'Contact created'or values['message_type'] == 'notification':
                        return super(MailMessage, self).create(values)
                    elif 'client_message_id' not in values:
                        if 'model' in values:
                            if values['model'] == 'discuss.channel':
                                if self.env.user.sl_slack_user_id and self.env.user.sl_slack_user_name:
                                    channel = self.env['discuss.channel'].search([('id', '=', values['res_id'])])
                                    if channel.channel_type == 'channel':
                                        if values['attachment_ids']:
                                            message=values['body']
                                            for attachment in values['attachment_ids']:
                                                attachment_data = self.env['ir.attachment'].sudo().search([('id', '=', attachment[1])])
                                                upload = sc.files_upload(content=base64.b64decode(attachment_data.datas),filename=attachment_data.name,mimetype=attachment_data.mimetype)
                                                message = message + "<" + upload['file']['permalink'] + "| >"
                                            message_post = sc.chat_postMessage(channel=channel['sl_slack_channel_id'],text=message)
                                            return super(MailMessage, self).create(values)
                                        else:
                                            sc.api_call("chat.postMessage", json={'channel': channel['sl_slack_channel_id'],'text': values['body'],'username': self.env.user.sl_slack_user_name,'icon_emoji': 'true'})
                                            return super(MailMessage, self).create(values)
                                    elif channel.channel_type == 'chat':
                                        # slack_user = self.env['discuss.channel'].search([('id', '=', values['res_id'])]).channel_partner_ids[0]
                                        slack_user_id = self.env['res.users'].search([('name', '=', values['record_name'])]).sl_slack_user_id
                                        # slack_user_id = slack_user.user_ids[0].sl_slack_user_id
                                        userChannel = sc.api_call("conversations.open", json={'users':slack_user_id})
                                        if userChannel:
                                            if values['attachment_ids']:
                                                message = values['body']
                                                for attachment in values['attachment_ids']:
                                                    attachment_data = self.env['ir.attachment'].sudo().search(
                                                        [('id', '=', attachment[1])])
                                                    upload = sc.files_upload(
                                                        content=base64.b64decode(attachment_data.datas),
                                                        filename=attachment_data.name, mimetype=attachment_data.mimetype)
                                                    message = message + "<" + upload['file']['permalink'] + "| >"
                                                send_message = sc.api_call(
                                                    "chat.postMessage", json={
                                                        'channel': userChannel['channel']['id'],
                                                        'text': message,
                                                        'username': self.env.user.sl_slack_user_name,
                                                        'icon_emoji': 'true'
                                                    })
                                                return super(MailMessage, self).create(values)
                                            else:
                                                send_message = sc.api_call(
                                                    "chat.postMessage",json={
                                                    'channel':userChannel['channel']['id'],
                                                    'text':values['body'],
                                                    'username':self.env.user.sl_slack_user_name,
                                                    'icon_emoji':'true'
                                                })
                                                return super(MailMessage, self).create(values)
                                    else:
                                        return super(MailMessage, self).create(values)
                                else:
                                    raise ValidationError('Please invite logged in user to slack before sending a message or please '
                                                     'disable slack to just send a normal message.')
                                return super(MailMessage, self).create(values)
                            else:
                                return super(MailMessage, self).create(values)
                        else:
                            return super(MailMessage, self).create(values)
                    else:
                        return super(MailMessage, self).create(values)
                else:
                    return super(MailMessage, self).create(values)
        except Exception as e:
            raise ValidationError(str(e))
