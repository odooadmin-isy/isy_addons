# -*- coding: utf-8 -*-
{
    'name': 'ISY - Budget Available Amount',
    'summary': 'Show available budget amount after reserved commitments',
    'version': '1.0.0',
    'description': """
        Display available budget amount per account for the current fiscal year,
        considering remaining balance and reserved amounts from purchase orders,
        employee advances, reimbursements, and draft journal entries.
    """,
    'author': 'ISY Odoo Team',
    'company': 'The International School Yangon',
    'website': 'https://www.isyedu.org',
    'category': 'Accounting',
    'depends': [
        'base',
        'accounting_budget_extension_V7',
        'mt_isy',
        'purchase',
        'account',
        'employee_expense_advance',
    ],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/budget_available_amount_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
