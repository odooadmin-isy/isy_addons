# -*- coding: utf-8 -*-
{
    'name': 'Book Donation Request',
    'summary': 'Librarian book donation list requests with two-step approval',
    'description': """
        Librarians submit lists of proposed book donations.
        Each request goes through first and second approval before it is accepted.
    """,
    'author': 'ISY Team',
    'website': 'https://isyedu.org',
    'category': 'ISY Modules',
    'version': '17.0.1.4.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'stock', 'isy_ticketing', 'mt_isy'],
    'data': [
        'data/portal_cleanup.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/book_donation_request_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
