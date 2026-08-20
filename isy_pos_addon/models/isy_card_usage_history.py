# -*- coding: utf-8 -*-

from odoo import models, fields

class CardUsageHistory(models.Model):
    _name = 'isy.card.usage.history'
    _description = 'ISY Card Usage History'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    name = fields.Char(string='Name', related='partner_id.name')
    barcode = fields.Char(string='Barcode')
    student_number = fields.Char(string='Student Number')
    amount = fields.Float(string='Amount', required=True)
    ptype = fields.Char(string='Payment Type')
    order_ref = fields.Char(string='Order Reference')
    pos_config_id = fields.Many2one('pos.config', string='Point of Sale')
