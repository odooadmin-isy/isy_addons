# -*- coding: utf-8 -*-

from odoo import models, fields

class CardUsageHistory(models.Model):
    _name = 'isy.card.usage.history'
    _description = 'ISY Card Usage History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    name = fields.Char(string='Name', related='partner_id.name')
    barcode = fields.Char(string='Barcode', related='partner_id.card_barcode', store=True)
    student_number = fields.Char(string='Student Number', related='partner_id.student_number', store=True)
    amount = fields.Float(string='Amount', required=True)
    ptype = fields.Char(string='Payment Type')
    order_ref = fields.Char(string='Order Reference')
