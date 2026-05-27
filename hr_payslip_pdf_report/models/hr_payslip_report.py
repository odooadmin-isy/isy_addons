# -*- coding: utf-8 -*-
from odoo import models, api

# Lines to hide from the payslip display
INVISIBLE_KEYWORDS = ['Retirement', 'Allowance', 'Fund']

# Lines to exclude from NET/Gross recalculation
EXCLUDED_KEYWORDS = ['Monthly Severance', 'Allowance']


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_visible_lines(self):
        """Return payslip lines excluding INVISIBLE_KEYWORDS."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: line.appears_on_payslip
                and line.amount != 0
                and not any(kw in (line.name or '') for kw in INVISIBLE_KEYWORDS)
        )

    def get_excluded_amount(self):
        """Sum of lines matching EXCLUDED_KEYWORDS."""
        self.ensure_one()
        return sum(self.line_ids.filtered(
            lambda l: any(kw in (l.name or '') for kw in EXCLUDED_KEYWORDS)
        ).mapped('amount'))

    def get_adjusted_net(self):
        """NET amount minus excluded lines."""
        self.ensure_one()
        net_amount = sum(self.line_ids.filtered(
            lambda l: ('NETLIT' in l.code or 'NETES' in l.code)
                      and 'PETTY' not in l.code
        ).mapped('amount'))
        return net_amount - self.get_excluded_amount()

    def get_monthly_gross_salary(self):
        """Monthly Gross Salary minus excluded lines."""
        self.ensure_one()
        gross_amount = sum(self.line_ids.filtered(
            lambda l: 'Monthly Salary' in (l.name or '')
        ).mapped('amount'))
        return gross_amount


class HrPayslipReportHandler(models.AbstractModel):
    _name = 'report.hr_payslip_pdf_report.report_payslip_template'
    _description = 'Payslip PDF Report Handler'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': self.env['hr.payslip'].browse(docids),
        }
