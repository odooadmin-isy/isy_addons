# -*- coding: utf-8 -*-

from odoo import models, fields

class PartnerCardBalance(models.TransientModel):
    _name = 'partner.card.balance'
    _description = 'Partner Card Balance'
    _order = 'name'

    name = fields.Char(string='Name', related='partner_id.name')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    student_number = fields.Char(string='Student Number', related='partner_id.student_number')
    balance = fields.Float(string='Balance', related='partner_id.card_balance')
    barcode = fields.Char(string='Barcode', related='partner_id.card_barcode')

class PartnerCardBalanceWizard(models.TransientModel):
    _name = 'partner.card.balance.wizard'
    _description = 'Partner Card Balance Wizard'

    barcode = fields.Char(string='Barcode', required=True)

    def action_search(self):
        self.ensure_one()
        barcode = self.barcode.lstrip('0')
        partner = self.env['res.partner'].search([('card_barcode', '=', barcode)], limit=1)
        if not partner:
            return False

        # Create transient record
        partner_card_balance = self.env['partner.card.balance'].sudo().create({
            'partner_id': partner.id,
        })

        view_id = self.env.ref('isy_pos_addon.view_partner_card_balance_tree')
        if partner:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'res_model': 'partner.card.balance',
                'views': [(view_id.id, 'tree')],
                'res_id': partner_card_balance.id,
                'domain': [('id', '=', partner_card_balance.id)],
                'context': {'active_test': False},
                'target': 'new',
            }