# -*- coding: utf-8 -*-
{
    'name': 'HR Payslip PDF Report',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Generate professional PDF payslip reports with server action',
    'description': """
        HR Payslip PDF Report
        =====================
        Professional PDF payslip report for Odoo 17:
        - Detailed payslip layout with company branding
        - Earnings & deductions breakdown
        - Worked days summary
        - Server action on list and form view (prints directly, no wizard)
        - Supports bulk print for multiple payslips
    """,
    'author': 'Custom Development',
    'depends': ['hr_payroll'],
    'data': [
        'report/payslip_report_template.xml',
        'report/payslip_report.xml',
        'wizard/print_payslip_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
