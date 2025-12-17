# -*- coding: utf-8 -*-

from odoo import models, fields

class RechargeHistory(models.Model):
    _name = 'isy.card.recharge.history'
    _description = 'ISY Card Recharge History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    name = fields.Char(string='Name', related='partner_id.name')
    barcode = fields.Char(string='Barcode', related='partner_id.card_barcode', store=True)
    student_number = fields.Char(string='Student Number', related='partner_id.student_number', store=True)
    amount = fields.Float(string='Amount', required=True)
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now())
