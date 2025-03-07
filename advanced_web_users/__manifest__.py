{
    "name": "Advanced Web",
    "version": "17.0.1.1.0",
    "summary": "Set all relational fields domain by selecting its records unsing `in, not in` operator.",
    "sequence": 10,
    "author": "Odexa",
    "license": "OPL-1",
    "description": """
      
        """,
    "price": "20.00",
    "currency": "USD",
    "depends": ["base", "web"],
    "data": [
    ],
    "assets": {
        "web.assets_frontend": [
            "advanced_web_domain_widget/static/src/core/**/*",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.js",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.xml",
        ],
        "web._assets_core": [
            "advanced_web_domain_widget/static/src/core/**/*",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.js",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.xml",
        ],
        "web.assets_backend": [
            "advanced_web_domain_widget/static/src/core/**/*",
            "advanced_web_domain_widget/static/src/fields/domain/domain_field.js",
            "advanced_web_domain_widget/static/src/fields/domain/domain_field.xml",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.js",
            "advanced_web_domain_widget/static/src/dateSelectionBits/dateSelectionBits.xml",
        ],
    },
    "images": ["static/description/banner.png"],
    "application": True,
    "installable": True,
    "auto_install": False,
}
