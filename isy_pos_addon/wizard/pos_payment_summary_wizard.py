from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPaymentSummaryWizard(models.TransientModel):
    _name = 'pos.payment.summary.wizard'
    _description = 'POS Payment Summary Wizard'

    date_from = fields.Date(
        string='From Date', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='To Date', required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    config_ids = fields.Many2many(
        'pos.config', string='Points of Sale',
        domain=[('is_vendor_payment', '=', True)],
        help='Leave empty to include all points of sale.',
    )
    available_payment_method_ids = fields.Many2many(
        'pos.payment.method',
        compute='_compute_available_payment_method_ids',
        string='Available Payment Methods',
    )
    payment_method_ids = fields.Many2many(
        'pos.payment.method', string='Payment Methods',
        # distinct relation table from the one above, or they collide
        relation='pos_payment_summary_wizard_method_rel',
        column1='wizard_id', column2='method_id',
        help='Leave empty to include all payment methods.',
    )

    @api.depends('config_ids')
    def _compute_available_payment_method_ids(self):
        all_configs = self.env['pos.config'].search([('is_vendor_payment', '=', True)])
        all_methods = all_configs.mapped('payment_method_ids')
        for wiz in self:
            if wiz.config_ids:
                wiz.available_payment_method_ids = wiz.config_ids.mapped('payment_method_ids')
            else:
                wiz.available_payment_method_ids = all_methods

    @api.onchange('config_ids')
    def _onchange_config_ids(self):
        """Drop any already-picked method that the new config selection doesn't offer."""
        if self.config_ids:
            valid = self.config_ids.payment_method_ids
            self.payment_method_ids = self.payment_method_ids & valid

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from > wiz.date_to:
                raise UserError(_('The "From Date" must be earlier than the "To Date".'))

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('payment_date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('payment_date', '<', fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)),
            ('pos_order_id.state', 'in', ['paid', 'done', 'invoiced']),
        ]
        if self.config_ids:
            domain.append(('pos_order_id.config_id', 'in', self.config_ids.ids))
        else:
            domain.append(('pos_order_id.config_id', 'in', self.env['pos.config'].search([('is_vendor_payment', '=', True)]).ids))

        if self.payment_method_ids:
            domain.append(('payment_method_id', 'in', self.payment_method_ids.ids))
        return domain

    def get_summary(self):
        """Return (methods, rows) where rows is a list of
        (date, {method_id: amount}, day_total), one entry per day with activity.
        """
        self.ensure_one()
        payments = self.env['pos.payment'].search(self._get_domain())

        # Columns: the filtered methods, or every method that actually appears.
        methods = self.payment_method_ids or payments.mapped('payment_method_id')
        methods = methods.sorted('name')

        buckets = defaultdict(lambda: defaultdict(float))
        for payment in payments:
            # UTC -> user timezone, so a 23:30 payment lands on the right day.
            local_dt = fields.Datetime.context_timestamp(self, payment.payment_date)
            buckets[local_dt.date()][payment.payment_method_id.id] += payment.amount

        rows = []
        for day in sorted(buckets):
            per_method = buckets[day]
            rows.append((day, per_method, sum(per_method.values())))
        return methods, rows

    def action_generate_report(self):
        self.ensure_one()
        methods, rows = self.get_summary()
        if not rows:
            raise UserError(_('No payments found for the selected filters.'))
        action = self.env.ref('isy_pos_addon.action_pos_payment_summary_xlsx').report_action(self)
        action['close_on_report_download'] = True
        return action
