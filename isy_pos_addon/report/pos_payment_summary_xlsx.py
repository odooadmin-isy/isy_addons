from odoo import models


class PosPaymentSummaryXlsx(models.AbstractModel):
    _name = 'report.isy_pos_addon.pos_payment_summary_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'POS Payment Summary XLSX'

    def generate_xlsx_report(self, workbook, data, wizards):
        wizard = wizards[0]
        methods, rows = wizard.get_summary()

        sheet = workbook.add_worksheet('Daily Payments')

        title = workbook.add_format({'bold': True, 'font_size': 14})
        bold = workbook.add_format({'bold': True})
        header = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        })
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})
        money = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        row_total = workbook.add_format({
            'border': 1, 'bold': True, 'num_format': '#,##0.00', 'bg_color': '#F2F2F2',
        })
        grand = workbook.add_format({
            'border': 1, 'bold': True, 'num_format': '#,##0.00', 'bg_color': '#FCE4D6',
        })

        sheet.write(0, 0, 'Period: %s to %s' % (wizard.date_from, wizard.date_to), bold)

        # Header: Date | <method 1> | <method 2> | ... | Total
        head_row = 2
        sheet.write(head_row, 0, 'Date', header)
        sheet.set_column(0, 0, 14)
        for i, method in enumerate(methods, start=1):
            sheet.write(head_row, i, method.name, header)
            sheet.set_column(i, i, 16)
        total_col = len(methods) + 1
        sheet.write(head_row, total_col, 'Total', header)
        sheet.set_column(total_col, total_col, 16)
        sheet.freeze_panes(head_row + 1, 1)

        column_totals = {m.id: 0.0 for m in methods}
        grand_total = 0.0

        r = head_row
        for day, per_method, day_total in rows:
            r += 1
            sheet.write_datetime(r, 0, day, date_fmt)
            for i, method in enumerate(methods, start=1):
                amount = per_method.get(method.id, 0.0)
                sheet.write_number(r, i, amount, money)
                column_totals[method.id] += amount
            sheet.write_number(r, total_col, day_total, row_total)
            grand_total += day_total

        r += 1
        sheet.write(r, 0, 'Total', header)
        for i, method in enumerate(methods, start=1):
            sheet.write_number(r, i, column_totals[method.id], row_total)
        sheet.write_number(r, total_col, grand_total, grand)
