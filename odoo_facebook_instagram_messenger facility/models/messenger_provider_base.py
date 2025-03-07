import json
import secrets
import string
import time

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class MessengerProvider(models.Model):
    _name = "messenger.provider"
    _description = "Add Provider to configure the instagram and messenger"

    name = fields.Char("Name", required=True)
    provider = fields.Selection(
        string="Provider",
        required=True,
        selection=[("none", "No Provider Set"), ("graph_api", "Graph API")],
        default="none",
    )
    state = fields.Selection(
        string="State",
        selection=[("disabled", "Disabled"), ("enabled", "Enabled")],
        default="enabled",
        required=True,
        copy=False,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
    )

    graph_api_url = fields.Char(string="API URL")
    graph_api_token = fields.Char(string="Token")
    username = fields.Char("Username", readonly=True)
    account_id = fields.Char("Account ID", readonly=True)
    graph_api_authentication = fields.Selection(
        [
            ("no_auth", "No Auth"),
            ("basic_auth", "Basic Auth"),
            ("bearer_token", "Bearer Token"),
        ],
        default="no_auth",
        string="Authentication",
    )
    graph_api_authenticated = fields.Boolean("Authenticated")
    user_id = fields.Many2one(string="User", comodel_name="res.users")

    is_token_generated = fields.Boolean("Is Token Generated")
    call_back_url = fields.Html(string="Call Back URL & Verify Token")

    def GenerateMessengerVerifyToken(self):
        seconds = time.time()
        unix_time_to_string = str(seconds).split(".")[
            0
        ]  # time.time() generates a float example 1596941668.6601112
        alphaNumeric = string.ascii_uppercase + unix_time_to_string
        alphaNumericlower = string.ascii_lowercase + unix_time_to_string
        firstSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        secondSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        thirdSet = "".join(secrets.choice(alphaNumericlower) for i in range(4))
        forthSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        fifthset = "".join(secrets.choice(alphaNumericlower) for i in range(4))
        token = firstSet + secondSet + thirdSet + forthSet + fifthset
        return token

    def messenger_reload_with_get_status(self):
        if self.graph_api_url and self.graph_api_token:
            url = "%s/me?access_token=%s" % (self.graph_api_url, self.graph_api_token)
            page = requests.get(url)
            page_content = page.json()
            if not page_content.get("error"):
                url = "%s/%s?fields=name,username,followers_count&access_token=%s" % (
                    self.graph_api_url,
                    page_content["id"],
                    self.graph_api_token,
                )
                val = requests.get(url)
                content = val.json()
                if content.get("username"):
                    self.username = content["username"]
                if content.get("id"):
                    self.account_id = content["id"]

            payload = {
                "full": True,
            }
            headers = {}
            try:
                response = requests.request("GET", url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if response.status_code == 200:
                dict = json.loads(response.text)
                if dict["id"] == self.account_id:
                    self.graph_api_authenticated = True

                    IrConfigParam = self.env["ir.config_parameter"].sudo()
                    base_url = IrConfigParam.get_param("web.base.url", False)

                    data = {"webhookUrl": base_url + "/graph_api/webhook"}
                    verify_token = self.GenerateMessengerVerifyToken()
                    self.call_back_url = (
                        '<p>Now, You can set below details to your facebook configurations.</p><p>Call Back URL: <u><a href="%s">%s</a></u></p><p>Verify Token: <u style="color:#017e84">%s</u></p>'
                        % (data.get("webhookUrl"), data.get("webhookUrl"), verify_token)
                    )
                    self.is_token_generated = True
            else:
                self.graph_api_authenticated = False
                self.call_back_url = "<p>Oops, something went wrong, Kindly Double Check the above Credentials. </p>"

    def messenger_send_message(self, recipient, message, quotedMsgId=False):
        t = type(self)
        if self.provider != "none":
            fn = getattr(t, f"{self.provider}_messenger_send_message", None)
            # eval_context = self._get_eval_context(self)
            # active_id = self._context.get('active_id')
            # run_self = self.with_context(active_ids=[active_id], active_id=active_id)
            res = fn(self, recipient, message, quotedMsgId)
            return res
        else:
            raise UserError(_("No Provider Set, Please Enable Provider"))

    def graph_api_messenger_send_message(self, recipient, message, quotedMsgId):
        if self.graph_api_authenticated:
            payload = json.dumps(
                {
                    "recipient": {"id": recipient.messenger_account_id},
                    "message": {"text": message},
                    "access_token": self.graph_api_token,
                }
            )
            url = (
                self.graph_api_url
                + self.account_id
                + "/messages?access_token="
                + self.graph_api_token
            )
            headers = {"Content-Type": "application/json"}
            try:
                answer = requests.post(url, data=payload, headers=headers)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your messenger.")

    def messenger_send_media(self, media_url, recipient, sent_type, attachment_id):
        t = type(self)
        fn = getattr(t, f"{self.provider}_messenger_send_media", None)
        res = fn(self, media_url, recipient, sent_type, attachment_id)
        return res

    def graph_api_messenger_send_media(
        self, media_url, recipient, sent_type, attachment_id
    ):
        if self.graph_api_authenticated:
            url = self.graph_api_url + self.account_id + "/messages"
            data = {
                "recipient": {"id": recipient.messenger_account_id},
                "message": {
                    "attachment": {
                        "type": sent_type,
                        "payload": {
                            "url": media_url
                        }
                    }
                }
            }
            payload = json.dumps(data)
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.graph_api_token,
            }
            try:
                answer = requests.post(url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your messenger.")

    # def messenger_get_media_id(self, media_id, recipient, sent_type, attachment_id):
    #     if self.graph_api_authenticated:
    #         url = self.graph_api_url + self.account_id + "/messages"
    #         data = {
    #             "recipient": {
    #                 "id": recipient.messenger_account_id
    #             },
    #             "message": {
    #                 "attachment": {
    #                     "type": sent_type,
    #                     "payload": {
    #                         "url": media_id,
    #                     }
    #                 }
    #             }
    #         }
    #         payload = json.dumps(data)
    #         headers = {
    #             'Content-Type': 'application/json',
    #             'Authorization': 'Bearer ' + self.graph_api_token
    #         }
    #         try:
    #             answer = requests.post(url, headers=headers, data=payload)
    #         except requests.exceptions.ConnectionError:
    #             raise UserError(
    #                 ("please check your internet connection."))
    #         if answer.status_code != 200:
    #             if json.loads(answer.text) and 'error' in json.loads(answer.text):
    #                 if 'error_user_msg' in json.loads(answer.text).get('error') and 'error_user_title' in json.loads(answer.text).get('error'):
    #                     dict = 'Title  :  ' + json.loads(answer.text).get('error').get('error_user_title') +'\nMessage  :  '+  json.loads(answer.text).get('error').get('error_user_msg')
    #                     raise UserError(_(dict))
    #                 if 'message' in json.loads(answer.text).get('error'):
    #                     dict = json.loads(answer.text).get('error').get('message')
    #                     raise UserError(_(dict))
    #         return answer
    #     else:
    #         raise UserError(
    #             ("please authenticated your whatsapp."))

    def instagram_send_message(self, recipient, message, quotedMsgId=False):
        t = type(self)
        if self.provider != "none":
            fn = getattr(t, f"{self.provider}_instagram_send_message", None)
            # eval_context = self._get_eval_context(self)
            # active_id = self._context.get('active_id')
            # run_self = self.with_context(active_ids=[active_id], active_id=active_id)
            res = fn(self, recipient, message, quotedMsgId)
            return res
        else:
            raise UserError(_("No Provider Set, Please Enable Provider"))

    def graph_api_instagram_send_message(self, recipient, message, quotedMsgId):
        if self.graph_api_authenticated:
            payload = json.dumps(
                {
                    "recipient": {"id": recipient.instagram_account_id},
                    "message": {"text": message},
                    "access_token": self.graph_api_token,
                }
            )
            url = (
                self.graph_api_url
                + self.account_id
                + "/messages?access_token="
                + self.graph_api_token
            )
            headers = {"Content-Type": "application/json"}
            try:
                answer = requests.post(url, data=payload, headers=headers)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your instagram.")

    def instagram_send_media(self, media_url, recipient, sent_type, attachment_id):
        t = type(self)
        fn = getattr(t, f"{self.provider}_instagram_send_media", None)
        res = fn(self, media_url, recipient, sent_type, attachment_id)
        return res

    def graph_api_instagram_send_media(
        self, media_url, recipient, sent_type, attachment_id
    ):
        if self.graph_api_authenticated:
            url = self.graph_api_url + self.account_id + "/messages"
            data = {
                "recipient": {"id": recipient.instagram_account_id},
                "message": {
                    "attachment": {"type": sent_type, "payload": {"url": media_url}}
                },
            }
            payload = json.dumps(data)
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.graph_api_token,
            }
            try:
                answer = requests.post(url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your instagram.")
