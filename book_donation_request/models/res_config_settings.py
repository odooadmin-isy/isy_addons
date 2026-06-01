# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    book_donation_second_approver_id = fields.Many2one(
        'res.users',
        string='Default Second Approver',
        config_parameter='isy.default_second_approver_id',
        domain="[('share', '=', False)]",
    )
