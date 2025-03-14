# -*- coding: utf-8 -*
# This Source Codes created by TL Technology (thanhchatvn@gmail.com)
# Not allow resale, editing source codes
# License: Odoo Proprietary License v1.0
{
    "name": "Point Of Sale Offline Mode",
    "version": "1.0.3",
    "category": "Point of Sale",
    "author": "By Odexa",
    "summary":
        """
        Point Of Sale Offline Mode\n
        Allow Sale Products, create Orders without Internet and Odoo Server \n
        Allow Reload, Refresh POS Page  without Internet and Odoo Server\n
        Allow Resume POS Session without Internet and Odoo Server
        """,
    "description":
        """
        Point Of Sale Offline Mode\n
        Allow Sale Products, create Order without Internet and Odoo Server \n
        Allow Reload, Refresh POS Page  without Internet and Odoo Server\n
        Allow Resume POS Session without Internet and Odoo Server
        """,
    "price": "120",
    "sequence": 0,
    "depends": [
        "point_of_sale",
        "pos_hr",
        "pos_restaurant",
    ],
    "demo": [],
    "data": [
        "import_libraries.xml"
    ],
    "currency": "EUR",
    "installable": True,
    "application": True,
    "images": ["static/description/icon.png"],
    "license": "OPL-1",
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_retail_offline/static/src/apps/idb-keyval.js",
            "pos_retail_offline/static/src/apps/PosIDB.js",
            "pos_retail_offline/static/src/apps/models.js",
            "pos_retail_offline/static/src/apps/webClient.js",
        ],
        'web.assets_backend': [

        ],
    },
}
