# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from slack import WebClient
import base64
import time
from datetime import datetime
import requests
from slack.errors import SlackApiError


class SlackSettingModel(models.TransientModel):
    _inherit = 'res.config.settings'

    sl_is_slack = fields.Boolean('Slack', default=False)
    sl_client_id = fields.Char('Client Id')
    sl_client_secret = fields.Char('Client Secret')
    sl_is_import_users = fields.Boolean('Slack Users', default=False)
    sl_is_import_channels = fields.Boolean('Slack Channels', default=False)

    def set_values(self):
        res = super(SlackSettingModel, self).set_values()
        self.env['ir.config_parameter'].set_param('odoo_slack.sl_is_slack', self.sl_is_slack)
        self.env['ir.config_parameter'].set_param('odoo_slack.sl_client_id', self.sl_client_id)
        self.env['ir.config_parameter'].set_param('odoo_slack.sl_client_secret', self.sl_client_secret)
        self.env['ir.config_parameter'].set_param('odoo_slack.sl_is_import_users', self.sl_is_import_users)
        self.env['ir.config_parameter'].set_param('odoo_slack.sl_is_import_channels', self.sl_is_import_channels)

        return res

    @api.model
    def get_values(self):
        res = super(SlackSettingModel, self).get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        is_slack = IrConfigParameter.get_param('odoo_slack.sl_is_slack')
        client_id = IrConfigParameter.get_param('odoo_slack.sl_client_id')
        client_secret = IrConfigParameter.get_param('odoo_slack.sl_client_secret')
        is_im_users = IrConfigParameter.get_param('odoo_slack.sl_is_import_users')
        is_im_channels = IrConfigParameter.get_param('odoo_slack.sl_is_import_channels')

        res.update(
            sl_is_slack=True if is_slack == 'True' else False,
            sl_client_id=client_id,
            sl_client_secret=client_secret,
            sl_is_import_users=True if is_im_users == 'True' else False,
            sl_is_import_channels=True if is_im_channels == 'True' else False,
        )

        return res

    def test_credentials(self):
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            client_id = IrConfigParameter.get_param('odoo_slack.sl_client_id')
            return {
                'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': 'https://slack.com/oauth/v2/authorize?user_scope=users:read,users:read.email,mpim:history,groups:history,groups:read,mpim:read,im:read,channels:history,channels:read,'
                       'channels:write,files:read,im:write,chat:write&client_id=' + client_id
            }
        except Exception as e:
            raise ValidationError(str(e))

    def import_slack_users(self):
        try:
            token = self.env['ir.config_parameter'].get_param('odoo_slack.access_token')
            sc = WebClient(token)
            slack_users = sc.api_call('users.list')
            users = slack_users['members']
            for user in users:
                if user['name'] != 'slackbot' and 'email' in user['profile'] and user['deleted']==False:
                    odoo_user = self.env['res.users'].search([('login', '=', user['profile']['email'])])
                    if not odoo_user:
                        self.env['res.users'].create({
                            'sl_slack_user_id': user['id'],
                            'sl_slack_user_name': user['profile']['real_name'],
                            'name': user['profile']['real_name'],
                            'login': user['profile']['email'],
                            'email': user['profile']['email'],
                        })
                    else:
                        odoo_user.write({
                            'sl_slack_user_id': user['id'],
                            'sl_slack_user_name': user['profile']['real_name'],
                            'name': user['profile']['real_name'],
                        })
                    self.env.cr.commit()
        except Exception as e:
            raise ValidationError(str(e))

    def import_slack_channels(self):
        try:
            token = self.env['ir.config_parameter'].get_param('odoo_slack.access_token')
            sc = WebClient(token)
            slack_channels = sc.api_call('conversations.list',params={"types":"public_channel,private_channel,mpim,im"})
            for channel in slack_channels['channels']:
                # time.sleep(15)
                if 'is_channel' in channel:
                    partner_ids = self._get_channel_users(sc, channel['id'])
                    messages_ids = self._get_channel_messages(sc, channel['id'],token)
                    odoo_channel = self.env['discuss.channel'].search([('name', '=', channel['name'])])
                    if not odoo_channel:
                        self.env['discuss.channel'].create({
                            'sl_slack_channel_id': channel.get('id'),
                            'name': channel.get('name'),
                            # 'alias_user_id': self.env.user.id,
                            'is_member': True,
                            'channel_partner_ids': partner_ids,
                            'message_ids': messages_ids,
                        })
                        self.env.cr.commit()
                    else:
                        odoo_channel.write({
                            'sl_slack_channel_id': channel.get('id'),
                            'name': channel.get('name'),
                            # 'alias_user_id': self.env.user.id,
                            'is_member': True,
                            'channel_partner_ids': partner_ids,
                            'message_ids': messages_ids,
                        })
                        self.env.cr.commit()
                else:
                    if channel['is_user_deleted'] == True or channel['user'] == 'USLACKBOT':
                        pass
                    else:
                        partners = []
                        user = self.env['res.users'].sudo().search([('sl_slack_user_id', '=', channel['user'])])
                        partner_ids = self._get_channel_users(sc, channel['id'])
                        for partner in partner_ids:
                            user_partner = self.env['res.partner'].sudo().search([('id', '=', partner[1])])
                            if user_partner.name == self.env.user.name or user_partner.name == user.name:
                                partners.append((4,user_partner.id))
                        messages_ids = self._get_channel_messages(sc, channel['id'], token)
                        odoo_channel = self.env['discuss.channel'].search([('sl_slack_channel_id', '=', channel['id'])])
                        if not odoo_channel:
                            self.env['discuss.channel'].sudo().create({
                                'sl_slack_channel_id': channel.get('id'),
                                'name': user.name,
                                'channel_type': 'chat',
                                'id': self.env.user.id,
                                'is_member': True,
                                'channel_partner_ids': partners,
                                'message_ids': messages_ids
                            })
                            self.env.cr.commit()
                        else:
                            odoo_channel.sudo().write({
                                'sl_slack_channel_id': channel.get('id'),
                                'name': user.name,
                                'public': 'private',
                                'channel_type': 'chat',
                                'alias_user_id': self.env.user.id,
                                'is_member': True,
                                'channel_partner_ids': partners,
                                'message_ids': messages_ids,
                            })
                            self.env.cr.commit()

        except Exception as e:
            raise ValidationError(str(e))

    def _get_channel_users(self, sc, channel_id):
        try:
            partner_ids = []
            channel_users = sc.api_call('users.list',json={'channel': channel_id})
            if channel_users["members"]:
                users = channel_users['members']
                for user in users:
                    if user['name'] != 'slackbot' and 'email' in user['profile']:
                        odoo_user = self.env['res.users'].search([('login', '=', user['profile']['email'])])
                        if not odoo_user:
                            odoo_user = self.env['res.users'].create({
                                'sl_slack_user_id': user['id'],
                                'name': user['profile']['real_name'],
                                'sl_slack_user_name': user['profile']['real_name'],
                                'login': user['profile']['email'],
                                'email': user['profile']['email'],
                            })
                        else:
                            odoo_user.write({
                                'sl_slack_user_id': user['id'],
                                'sl_slack_user_name': user['profile']['real_name'],
                            })
                        self.env.cr.commit()
                        partner_ids.append((4,odoo_user.partner_id.id))
            return partner_ids
        except Exception as e:
            raise ValidationError(str(e))

    def _get_private_channel_users(self, sc, channel_id):
        try:
            partner_ids = []
            channel_users = sc.api_call('users.list',json={'channel': channel_id})
            if channel_users["members"]:
                users = channel_users['members']
                for user in users:
                    if user['name'] != 'slackbot' and 'email' in user['profile']:
                        odoo_user = self.env['res.users'].search([('login', '=', user['profile']['email'])])
                        if not odoo_user:
                            odoo_user = self.env['res.users'].create({
                                'sl_slack_user_id': user['id'],
                                'name': user['profile']['real_name'],
                                'sl_slack_user_name': user['profile']['real_name'],
                                'login': user['profile']['email'],
                                'email': user['profile']['email'],
                            })
                        else:
                            odoo_user.write({
                                'sl_slack_user_id': user['id'],
                                'sl_slack_user_name': user['profile']['real_name'],
                            })
                        self.env.cr.commit()
                        partner_ids.append(odoo_user.partner_id.id)
            return partner_ids
        except Exception as e:
            raise ValidationError(str(e))

    def _get_channel_messages(self, sc, channel_id,token):
        try:
            messages_ids = []
            channel_messages = sc.api_call('conversations.history', params={'channel': channel_id})
            recipient_partner = self.env.user.commercial_partner_id.id
            for message in channel_messages['messages']:
                salck_attachment_ids = []
                if 'client_msg_id' in message:
                    mail_message = self.env['mail.message'].search(
                        [('client_message_id', '=', message['client_msg_id'])])
                    if not mail_message:
                        if 'files' in message:
                            for file in message['files']:
                                file_redundency_check = self.env['ir.attachment'].search([(('sl_attachment_id', '=', file['id']))])
                                if file_redundency_check:
                                    salck_attachment_ids.append(file_redundency_check.id)
                                else:
                                    if 'url_private' in file:
                                        url = file['url_private']
                                        response = requests.get(url=url, headers={
                                            'Accept': 'application/json',
                                            'Authorization': 'Bearer ' + token
                                        })
                                        msg = base64.b64encode(response.content)
                                        attachment_id = self.env['ir.attachment'].create({
                                            'name': file['name'],
                                            'datas': msg,
                                            'sl_attachment_id': file['id']
                                        })
                                        self.env.cr.commit()
                                        salck_attachment_ids.append(attachment_id.id)
                            ts = float(message['ts'])
                            date_time = datetime.fromtimestamp(ts)
                            message_creator = self.env['res.users'].search([('sl_slack_user_id', '=', message['user'])])
                            messages_ids.append((0,0,{
                                'subject': message['text'],
                                'attachment_ids' : [[6,0,salck_attachment_ids]],
                                'date': date_time,
                                'model': 'discuss.channel',
                                'res_id': recipient_partner,
                                'body': message['text'],
                                'client_message_id': message['client_msg_id'],
                                'email_from': message_creator.email,
                                'author_id': message_creator.partner_id.id,
                                'message_type': 'comment'
                            }))
                            self.env.cr.commit()
                        else:
                            ts = float(message['ts'])
                            date_time = datetime.fromtimestamp(ts)
                            message_creator = self.env['res.users'].search([('sl_slack_user_id', '=', message['user'])])
                            messages_ids.append((0,0,{
                                'subject': message['text'],
                                'date': date_time,
                                'body': message['text'],
                                'model': 'discuss.channel',
                                'res_id': recipient_partner,
                                'client_message_id': message['client_msg_id'],
                                'email_from': message_creator.email,
                                'author_id': message_creator.partner_id.id,
                                'message_type': 'comment'
                            }))
            return messages_ids
        except Exception as e:
            raise ValidationError(str(e))

class SlackAttachmentSetting(models.Model):
    _inherit = 'ir.attachment'

    sl_attachment_id = fields.Char('Slack Attachment Id')