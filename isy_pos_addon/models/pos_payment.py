# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    use_card = fields.Boolean(string='Use Card Payment')
    send_email = fields.Boolean(string='Send Email')
