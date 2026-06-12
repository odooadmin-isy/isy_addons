# -*- coding: utf-8 -*-
{
    'name': 'Portal Acknowledgment',
    'summary': 'Portal form with 3 tabs (read, video, read) and email on submit',
    'description': """
        Employees complete a portal acknowledgment with three tabs:
        reading content, watching an embedded YouTube video, and reading more content.
        On submit, an email is sent to their manager and the communication coordinator.
    """,
    'author': 'ISY Team',
    'website': 'https://isyedu.org',
    'category': 'Human Resources',
    'version': '17.0.1.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'portal', 'website', 'mail', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/acknowledgment_submission_views.xml',
        'views/acknowledgment_campaign_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
