
from odoo import models, fields, api, _
import random

import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = "res.users"

    aliexpress_token = fields.Char("AliExpress Token", copy=False)

    def generate_aliexpress_token(self):
        # the token has an entropy of about 120 bits (6 bits/char * 30 chars)
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        token = ''.join(random.SystemRandom().choice(chars) for _ in range(30))
        # token = secrets.token_hex(16)
        self.aliexpress_token = token
        return True
