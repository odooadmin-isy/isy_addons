# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    card_barcode = fields.Char(string='Card Barcode', type='char', track_visibility='onchange')
    card_balance = fields.Float(string='Card Balance', readonly=True)

    def _is_barcode_in_use(self, partner, barcode):
        existing_partner = self.env['res.partner'].sudo().search([('card_barcode', '=', barcode), ('id', '!=', partner.id)])
        return bool(existing_partner)

    def write(self, values):
        if 'card_barcode' in values and values['card_barcode']:
            for rec in self:
                barcode = values['card_barcode']
                if self._is_barcode_in_use(rec, barcode):
                    raise UserError("Barcode already in use.")

        return super(ResPartner, self).write(values)
