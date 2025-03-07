{
    "name": "Odoo Facebook Messenger Integration | Odoo Instagram Messaging Integration | Bidirectional with Facebook/Instagram Graph API by Meta odexa",
    "version": "17.0.0.1",
    "summary": """Odoo Facebook Messenger Integration and Odoo Instagram Messaging Integration (Bidirectional) with Facebook/Instagram Graph API by Meta
        Facebook
        Instagram
        Instagram Messenger
        Instagram connector
        Facebook connector
        Facebook Messenger
        Odoo Facebook
        Odoo Instagram
        Messenger
        Odoo Integration Facebook
        Odoo Integration Instagram
        Odoo Facebook Messenger
        Odoo Instagram Messenger""",
    "description": """Odoo Facebook Messenger Integration and Odoo Instagram Messaging Integration (Bidirectional) with Facebook/Instagram Graph API by Meta
        Facebook
        Instagram
        Instagram Messenger
        Instagram connector
        Facebook connector
        Facebook Messenger
        Odoo Facebook
        Odoo Instagram
        Messenger
        Odoo Integration Facebook
        Odoo Integration Instagram
        Odoo Facebook Messenger
        Odoo Instagram Messenger
    """,
    "category": "Discuss",
    "author": "Odexa",


    "license": "OPL-1",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/messenger_compose_message_view.xml",
        "wizard/instagram_compose_message_view.xml",
        "views/mail_channel.xml",
        "views/messenger_provider_base.xml",
        "views/messenger_history_views.xml",
        "views/instagram_history_views.xml",
        "views/messenger_channel_provider_line_views.xml",
        "views/res_partner_views_inherit.xml",
        "views/res_users_inherit.xml",
        "views/social_media_account_line_views.xml",
        "views/messenger_template_views.xml",
        "views/template_buttons_views.xml",
        "views/template_components_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_facebook_instagram_messenger/static/src/js/common/**/*",
        ],
    },
    "demo": [],
    "images": [
        "static/description/instaFbBidiraction.gif",
    ],
    "price": 100,
    "currency": "USD",
    "installable": True,
    "application": True,
    "auto_install": False,
}
