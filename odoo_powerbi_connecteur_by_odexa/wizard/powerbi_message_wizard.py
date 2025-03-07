# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Odexa Software Pvt. Ltd. (<https://Odexa.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.Odexa.com/license.html/>
#
##########################################################################

from odoo import fields, models

class MessageWizard(models.TransientModel):
    _name = "powerbi.message.wizard"
    _description = "Powerbi Message Wizard"
    
    text = fields.Text(string='Message', readonly=True, translate=True)
    def genrated_message(self, message, name='Message/Summary'):
        partial_id = self.create({'text':message}).id
        return {
            'name':name,
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'powerbi.message.wizard',
            'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }
