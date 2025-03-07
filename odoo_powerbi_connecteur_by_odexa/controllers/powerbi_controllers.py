# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Odexa Software Pvt. Ltd. (<https://Odexa.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.Odexa.com/license.html/>
#
##########################################################################

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class PowerbiControllers(http.Controller):

    @http.route("/get/reportparameter", auth="user", type="json")
    def get_report_parameter(self, res_id, **kw):
        reportObj = request.env['powerbi.report'].browse(res_id)
        data = {}
        if reportObj:
            resp = reportObj.get_report()
            data = {'embed_url':resp.get('embed_url'), 'embed_token':resp.get('embed_token'), 'token_expiry':resp.get('token_expiry')}
        return data

    @http.route("/get/dashboardparameter", auth="user", type="json")
    def get_dashboard_parameter(self, res_id, **kw):
        dashboardObj = request.env['powerbi.dashboard'].browse(res_id)
        data = {}
        if dashboardObj:
            resp = dashboardObj.get_dashboard()
            data = {'embed_url':resp.get('embed_url'), 'embed_token':resp.get('embed_token'), 'token_expiry':resp.get('token_expiry')}
        return data
