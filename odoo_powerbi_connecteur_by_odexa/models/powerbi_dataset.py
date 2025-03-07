# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Odexa Software Pvt. Ltd. (<https://Odexa.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.Odexa.com/license.html/>
#
##########################################################################

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError, RedirectWarning

_logger = logging.getLogger(__name__)

class PowerbiDataset(models.Model):
    _name = "powerbi.dataset"
    _inherit = ['mail.thread']
    _description = "Power BI Dataset"

    powerbiDatatypes = {
        "char": "string",
        "text": "string",
        "html":'string',
        "selection": "string",
        "float": "Double",
        "integer": "Int64",
        "monetary": "Double",
        "boolean": "bool",
        "many2one": "string",
        "date": "DateTime",
        "datetime": "DateTime",
        "many2many": "string",
        "one2many": "string"
    }
    name = fields.Char(string="Dataset Name", required=True)
    powerbi_id = fields.Char(string="Dataset Power BI Id", size=50, readonly=True)
    dataset_type = fields.Selection(
        [('perm','Permanent'),('temp','Temporary')],
        string="Type",
        default='perm',
        required=True,
        
    )
    state = fields.Selection(
        [('topublish','To Publish'),('published','Published')],
        compute="_compute_state",
        string="State",
        tracking=True
        
    )
    is_published = fields.Boolean(string="Is Published", default=False)
    workspace_id = fields.Many2one(
        "powerbi.workspace",
        string="Workspace",
        required=True,
        default=lambda self: self._compute_default_workspace()
    )
    table_ids = fields.One2many(
        "powerbi.table",
        inverse_name="dataset_id",
        string="Tables",
        readonly=True
    )
    count_total_table = fields.Integer(compute='_compute_tables',string='Tables')

    '''This Method Used to Count Related Tables Of Current Dataset'''
    def _compute_tables(self):
        total_table = self.env['powerbi.table'].search_count([('dataset_id','=',self.id)])
        self.count_total_table = total_table

    def _compute_default_workspace(self):
        return self._context.get('active_id')
   
    @api.depends("is_published")
    def _compute_state(self):
        for rec in self:
            if rec.is_published == True:
                rec.state = "published"
            else:
                rec.state = "topublish"

    '''This Method Used To Redirect To Related Tables of Current Dataset'''
    def action_redirect(self):
        model_name = self._context.get("model_name")
        name = self._context.get("name")
        domain = [('dataset_id','=',self.id)]
        return {
            "type":"ir.actions.act_window",
            'name':name,
            'res_model':model_name,
            'domain':domain,
            'view_mode':'tree,form',
            'target':'current'
            }

    def action_unpublish(self):
        return {
                'name':'Message/Summary',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'unpublish.message.wizard',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new'
            }

    '''This Method Used To Unpublish Dataset At Odoo end And Delete Powerbi At Powerbi End'''
    def unpublish_powerbi(self, dataset_operation, reason):
        msg = ""
        message=''
        msgModel = self.env["powerbi.message.wizard"]
        success, failure = [], []
        scopes = ['Dataset.ReadWrite.All']
        connObj = self.env["powerbi.connection"].get_active_connection()
        connection = connObj._create_powerbi_connection(scopes)
        for expObj in self:
            if dataset_operation == 'delete':
                if expObj.workspace_id.default_workspace:
                    url = f"{connObj.api_url}/datasets/{expObj.powerbi_id}"
                else:
                    url = f"{connObj.api_url}/groups/{expObj.workspace_id.powerbi_id}/datasets/{expObj.powerbi_id}"
                resp = self.env["powerbi.synchronization"].callPowerbiApi(url, 'delete', token=connection.get('token',''), scope=scopes)
                if resp.get('status', False):
                    expObj.powerbi_id = ''
                    expObj.is_published = False
                    expObj.table_ids.is_published = False
                    success.append(expObj.name)
                    message = f'Dataset {expObj.name} successfully deleted from Power Bi'+": Reason - "+reason
                    expObj.message_post(body=message)
                else:
                    failure.append(expObj.name)
                    message = "Dataset deletion error: Reason - "+str(resp.get("message"))
                    expObj.message_post(body=message)
            else:
                expObj.powerbi_id=''
                expObj.is_published = False
                expObj.table_ids.is_published = False
                message = f'Dataset {expObj.name} successfully unpublished on odoo'+": Reason - "+reason
                expObj.message_post(body=message)

        if success:
            msg+=f"{len(success)} dataset(s) successfully unpublished."
        if failure:
            msg+=f"{len(failure)} dataset(s) can't be unpublished."
        
        return msgModel.genrated_message(msg)

    def action_publish(self):
        return self.publish_to_powerbi()

    '''This Method Used To Publish Dataset At Powerbi End'''
    def publish_to_powerbi(self):
        success, failure, already_published, no_tables = [], [], [], []
        msg = ""
        msgModel = self.env["powerbi.message.wizard"]
        connObj = self.env["powerbi.connection"].get_active_connection()
        if not connObj:
            return msgModel.genrated_message("No active connection found!")
        scopes = ['Dataset.ReadWrite.All']
        connection = connObj._create_powerbi_connection(scopes)
        for expObj in self:
            if expObj.is_published:
                already_published.append(expObj.id)
                continue
            if expObj.workspace_id.default_workspace:
                url = f"{connObj.api_url}/datasets"
            else:
                url = f"{connObj.api_url}/groups/{expObj.workspace_id.powerbi_id}/datasets"
            tables = expObj.get_tables_data()
            if not tables:
                no_tables.append(expObj.id)
                continue
            data = {
                "name": expObj.name,
                "defaultMode": "Push",
                "tables": tables
            }
            resp = self.env["powerbi.synchronization"].callPowerbiApi(url, 'post', data, connection.get('token',''), scopes)
            if resp.get('status', False):
                value = resp.get('value')
                expObj.powerbi_id = value.get('id','')
                expObj.is_published = True
                expObj.table_ids.is_published = True
                success.append(expObj.name)
            else:
                failure.append(expObj.name)
               
        if success:
            msg+=f"{len(success)} dataset(s) successfully published."
        if failure:
            msg+="Dataset export error"+": Reason - "+str(resp.get("message"))
        if already_published:
            msg+=f"{len(already_published)} dataset(s) already published."
        if no_tables:
            msg+=f"{len(no_tables)} dataset(s) doesn't contain any table."
       
        return msgModel.genrated_message(msg)

    def get_tables_data(self):
        return_data = []
        for table in self.table_ids:
            table_data = {
                "name" : table.name,
                "columns" : self.get_table_columns(table)
            }
            return_data.append(table_data)
        return return_data
    
    '''This Method Used To Get Table Column Data'''
    def get_table_columns(self,table):
        columns = []
        for col in table.column_ids:
            if col.child_field_ids:
                for child in col.child_field_ids:
                    columns.append({
                        "name": child.field_description,
                        "dataType": self.powerbiDatatypes[child.ttype]
                    })
            else:
                columns.append({
                    "name" : col.field_id.field_description,
                    "dataType" : self.powerbiDatatypes[col.field_type]
                })
        return columns
