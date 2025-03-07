
from odoo import api, fields, models, tools, _

class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        result = super()._loader_params_res_company()
        result['search_params']['fields'].extend(
            ['write_date'])
        return result