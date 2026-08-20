from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CardUsageReportWizard(models.TransientModel):
    _name = 'card.usage.report.wizard'
    _description = 'Card Usage Report Wizard'

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    config_ids = fields.Many2many(
        'pos.config',
        string='Points of Sale',
        domain=[('is_vendor_payment', '=', True)],
        help='Leave empty to include all.',
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from > wiz.date_to:
                raise UserError(_('The "From Date" must be earlier than the "To Date".'))

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('create_date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('create_date', '<=', fields.Datetime.to_datetime(self.date_to)),
        ]

        if self.config_ids:
            domain.append(('pos_config_id', 'in', self.config_ids.ids))
        return domain

    def get_records(self):
        """Rows for the report. Adapt the model/fields to your usage data."""
        self.ensure_one()
        return self.env['isy.card.usage.history'].search(self._get_domain(), order='create_date asc')

    def action_generate_report(self):
        self.ensure_one()
        if not self.get_records():
            raise UserError(_('No records found for the selected period.'))
        action = self.env.ref(
            'isy_pos_addon.action_card_usage_xlsx'
        ).report_action(self)
        action['close_on_report_download'] = True
        return action
