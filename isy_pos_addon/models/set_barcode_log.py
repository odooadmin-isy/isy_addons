# -*- coding: utf-8 -*-

from odoo import models, fields

class SetBarcodeLog(models.Model):
    _name = 'isy.set.barcode.log'
    _description = 'ISY Set Barcode Log'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Partner')
    name = fields.Char(string='Name', related='partner_id.name')
    old_barcode = fields.Char(string='Old Barcode')
    new_barcode = fields.Char(string='New Barcode')
    amount = fields.Float(string='Current Balance', related='partner_id.card_balance')
