# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    card_barcode = fields.Char(string='Card Barcode', type='char', track_visibility='onchange')
    card_balance = fields.Float(string='Card Balance', readonly=True)
