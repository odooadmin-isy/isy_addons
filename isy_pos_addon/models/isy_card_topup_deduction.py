# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CardTopupDeduction(models.Model):
    _name = 'isy.card.topup.deduction'
    _description = 'ISY Card Topup/Deduction'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    name = fields.Char(string='Name', related='partner_id.name')
    usage_type = fields.Selection([('topup', 'Topup'), ('deduction', 'Deduction')], string='Type', required=True)
    barcode = fields.Char(string='Barcode')
    amount = fields.Float(string='Amount', required=True)
    date = fields.Datetime(string='Date', required=True, default=lambda self: fields.Datetime.now())
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State', required=True, default='draft')

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if self.barcode and self.barcode.lstrip('0') != '':
            partner = self.env['res.partner'].search(
                [('card_barcode', '=', self.barcode.lstrip('0'))],
                limit=1
            )
            self.partner_id = partner
        else:
            self.partner_id = False

    def action_topup(self):
        self.ensure_one()
        self.partner_id.card_balance += self.amount
        self.env['isy.card.recharge.history'].sudo().create({
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'ptype': 'Cash'
        })
        self.state = 'done'

    def action_deduction(self):
        self.ensure_one()
        self.partner_id.card_balance -= self.amount
        self.env['isy.card.usage.history'].sudo().create({
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'ptype': 'Deduction'
        })
        self.state = 'done'
