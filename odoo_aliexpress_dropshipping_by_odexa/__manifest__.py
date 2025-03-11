
{
  "name"                 :  "Odoo Connector Aliexpress & Dropshipping",
  "summary"              :  """With this module, you can now accept dropship orders for aliexpress on Odoo website. The customers can place orders for aliexpress products and you can forward them the Aliexpress website.""",
  "category"             :  "Website",
  "version"              :  "1.2.0",
  "sequence"             :  1,
  "author"               :  "Odexa ",
  "license"              :  "Other proprietary",
  "description"          :  """Dropshipper
Drop ship orders
Dropshipping
Odoo drop ship
Dropship delivery
Aliexpress integration
Odoo aliexpress dropship
Aliexpress delivery
Orders for aliexpress
Odoo dropshipping integration
Accept dropship orders
Import aliexpress products""",
  "depends"              :  [
                             'website_sale_stock',
                             'variant_price_extra',
                            ],
  "data"                 :  [
                             'security/aliexpress_security.xml',
                             'security/ir.model.access.csv',
                             'data/config_data.xml',
                             'views/res_users_view.xml',
                             'views/product_view.xml',
                             'views/aliexpress_products_view.xml',
                             'views/res_config_view.xml',
                             'views/sale_view.xml',
                             'views/menus_view.xml',
                             'views/template.xml',
                             'views/aliexpress_cron_view.xml',
                            ],
  "assets"            : {
        'web.assets_frontend':[
            'odoo_aliexpress_dropshipping/static/src/css/ali_product.css'
        ]
    },
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  95,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
