# -*- coding: utf-8 -*-

{
    'name': "ISY POS",
    'version': '17.0.1.0.0',
    'summary': """
        Support order lines' note
    """,
    'description': """
        Support order lines' note
    """,
    'author': "ISY",
    'website': "https://www.isyedu.org",
    'category': 'Point of sale',
    'depends': ['point_of_sale'],
    'data': [
       'views/res_partner_view.xml',
       'views/pos_view.xml',
       'views/recharge_history_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
        'isy_pos_addon/static/src/js/payment_screen.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
