# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Odexa Software Pvt. Ltd. (<https://Odexa.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.Odexa.com/license.html/>
#
##########################################################################

from odoo import fields, models, api

class UnpublishMessageWizard(models.TransientModel):
    _name = "unpublish.message.wizard"
    _description = "Unpublish Message Wizard"
    
    dataset_operation = fields.Selection(
        [('unlink','Unpublish only from Odoo end'),('delete','Delete dataset at the Power BI end')],
        string='Dataset Operation',
        default='unlink',
        required='True')
    reason=fields.Text(string="Reason to Unpublish", required=True)

    def unpublish_dataset(self):
        return self.env['powerbi.dataset'].browse(self._context.get('active_id')).unpublish_powerbi(self.dataset_operation, self.reason)
