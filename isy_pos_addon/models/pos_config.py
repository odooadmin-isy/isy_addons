# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_vendor_payment = fields.Boolean(string='Is Vendor Payment')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    commission_percentage = fields.Float(string='Commission Percentage')
    commission_journal_id = fields.Many2one('account.journal', string='Commission Journal')
    pos_payment_account_id = fields.Many2one('account.account', string='POS Payment Account')
    adjustment_account_id = fields.Many2one('account.account', string='Adjustment Account')
