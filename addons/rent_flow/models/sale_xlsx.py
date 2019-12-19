# __author__ = 'BinhTT'
from odoo import models, api
from datetime import datetime
import pytz


class SaleXlsx(models.AbstractModel):
    _name = 'report.rent_flow.report_xlsxsaleorder'
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, wb, data, sale):
        for obj in sale:
            wb.formats[0].set_font_size(8)
            self.line = 0

            sheet = wb.add_worksheet('Report')
            sheet.set_paper(9)
            sheet.repeat_rows(0, 6)
            sheet.fit_to_pages(1, 0)
            sheet.set_column(0, 30, 6)  # Width of columns B:D set to 30.
            sheet.set_footer('&L&P / &N')

            sheet.set_landscape()
            self.font = dict(font='Cambria')
            self.discount_total = 0
            money = wb.add_format({'num_format': '$#,##0'})
            # section1
            self.set_header_xlsx(wb, sheet, obj, 0, 12)
            self.set_header_xlsx(wb, sheet, obj, 14, 26)
            self.set_body(wb, sheet, obj, 0, 12)
            self.set_body(wb, sheet, obj, 14, 26)
            self.line_per_page = 45
            self.set_footer(wb, sheet, obj,  0, 12)
            self.set_footer(wb, sheet, obj, 14, 26)

    def set_header_xlsx(self, wb, sheet, obj, start, end):
        center_bold = wb.add_format({**self.font, 'align': 'center', 'bold': True})
        left_bold = wb.add_format({**self.font, 'align': 'left', 'bold': True})
        left_normal = wb.add_format({**self.font, 'align': 'left'})
        lien = 1
        if start != 0:
            lien = 2
        first_line = obj.company_id.name + ' - ' + obj.company_id.street+' - ' + obj.company_id.phone + ' (Liên '+str(lien)+')'
        line = self.line
        sheet.merge_range(line, start, line, end, first_line, center_bold)
        line += 1
        label1 = 'MÃ ĐƠN:'
        label2 = 'TỔNG NGÀY:'
        # line 2
        sheet.merge_range(line, start, line, start+2, label1, left_bold)
        sheet.merge_range(line, start+3, line, start+5, obj.name, left_normal)
        sheet.merge_range(line, start + 7, line, start + 9, label2, left_bold)
        sheet.write(line, start + 10, obj.date_rent, left_normal)

        line += 1
        label1 = 'NGÀY THUÊ:'
        label2 = 'NGÀY TRẢ:'
        # line3
        sheet.merge_range(line, start, line, start + 2, label1, left_bold)
        sheet.merge_range(line, start + 3, line, start + 5, self.convert_datetime_str(obj.date_order), left_normal)
        sheet.merge_range(line, start + 7, line, start + 9, label2, left_bold)
        sheet.merge_range(line, start + 10, line, start + 12, self.convert_datetime_str(obj.end_date), left_normal)

        line += 1
        label1 = 'KHÁCH HÀNG:'
        # line3
        sheet.merge_range(line, start, line, start + 2, label1, left_bold)
        sheet.merge_range(line, start + 3, line, end, obj.partner_id.name, left_normal)

        line += 1
        label1 = 'SĐT'
        # line3
        sheet.merge_range(line, start, line, start + 2, label1, left_bold)
        sheet.merge_range(line, start + 3, line, start + 5, obj.partner_id.phone, left_normal)
        # sheet.merge_range(line, start + 7, line, start + 9, '&CPage &P of &N', left_bold)
        if start != 0:
            self.line = line

    def convert_datetime_str(self, dt):
        dt_tz = dt.astimezone(pytz.timezone(self.env.user.tz))
        return dt_tz.strftime("%d/%m/%Y %H:%M")

    def set_body(self, wb, sheet, obj, start, end):
        line = self.line + 2
        sheet.set_row(line, 20)
        body_font = {**self.font, 'border': 1}
        center_bold = wb.add_format({**body_font, 'align': 'center', 'bold': True})
        left_bold = wb.add_format({**body_font, 'align': 'left', 'bold': True})
        left_normal = wb.add_format({**body_font, 'align': 'left'})
        right_normal = wb.add_format({**body_font, 'align': 'right', 'num_format': '#,##0'})
        # header table
        sheet.merge_range(line, start, line, start + 1, "MÃ HÀNG", left_bold)
        sheet.merge_range(line, start + 2, line, start + 5, "SẢN PHẨM", left_bold)
        sheet.write(line, start + 6, "SL", left_bold)
        sheet.merge_range(line, start + 7, line, start + 8, "GIÁ THUÊ", left_bold)
        sheet.merge_range(line, start + 9, line, start + 10, "GIẢM", left_bold)
        sheet.merge_range(line, start + 11, line, start + 12, "THÀNH TIỀN", left_bold)
        for order_line in obj.order_line:
            line += 1
            sheet.merge_range(line, start, line, start + 1, order_line.product_id.default_code, left_normal)
            sheet.merge_range(line, start + 2, line, start + 5, order_line.product_id.name, left_normal)
            sheet.write(line, start + 6, order_line.product_uom_qty, right_normal)
            sheet.merge_range(line, start + 7, line, start + 8, order_line.price_unit, right_normal)
            discount = order_line.discount_amount_manual
            if order_line.discount != 0:
                discount = order_line.price_unit * (1/discount)
            self.discount_total += discount or 0
            sheet.merge_range(line, start + 9, line, start + 10, discount if discount > 0 else '', right_normal)
            sheet.merge_range(line, start + 11, line, start + 12, order_line.price_subtotal, right_normal)
        if start != 0:
            self.line = line

    def set_footer(self, wb, sheet, obj, start, end):
        total_line = len(obj.order_line)
        line_excel_fit = self.line_per_page - 6
        page = int(total_line / line_excel_fit)
        if page * self.line_per_page - total_line < 26:
            page += 1
        bottom_start = page * self.line_per_page - 26

        footer_boder = {**self.font, 'border': 1}
        body_font = {**self.font}
        center_bold_top = wb.add_format({**body_font, 'align': 'center', 'bold': True, 'top': 1})
        center_bold = wb.add_format({**body_font, 'align': 'center', 'bold': True})
        left_bold = wb.add_format({**body_font, 'align': 'left', 'bold': True})
        left_normal = wb.add_format({**body_font, 'align': 'left'})
        left_bold_double = wb.add_format({**body_font, 'align': 'left', 'top': 6, 'bold': True})
        right_bold = wb.add_format({**body_font, 'align': 'right', 'num_format': '#,##0', 'bold': True})
        right_bold_double = wb.add_format({**body_font, 'align': 'right', 'num_format': '#,##0', 'top': 6,  'bold': True})
        sheet.merge_range(bottom_start, start + 4, bottom_start, start + 5, 'TỔNG', left_bold)
        sheet.write(bottom_start, start + 6, sum([line.product_uom_qty for line in obj.order_line]), right_bold)
        sheet.merge_range(bottom_start, start + 7, bottom_start, start + 8, '(sản phẩm)', left_normal)
        sheet.merge_range(bottom_start, start + 9, bottom_start, start + 10, self.discount_total/2, right_bold)
        sheet.merge_range(bottom_start, start + 11, bottom_start, start + 12, obj.amount_total, right_bold)
        bottom_start += 1
        sheet.merge_range(bottom_start, start + 4, bottom_start, start + 10, 'ĐẶT CỌC', left_bold_double)
        sheet.merge_range(bottom_start, start + 11, bottom_start, start + 12, obj.cash_outstanding if obj.state == 'done' else obj.cash_in, right_bold_double)
        bottom_start += 1
        sheet.merge_range(bottom_start, start, bottom_start, start + 9, '(Tôi đồng ý với các Quy định tại ' + obj.company_id.name + ')', left_normal)
        bottom_start += 1
        sheet.merge_range(bottom_start, start, bottom_start, start + 5, 'KHÁCH HÀNG KÝ NHẬN', center_bold_top)
        sheet.merge_range(bottom_start, start +7, bottom_start, start + 12, 'THU NGÂN', center_bold_top)
        bottom_start += 1
        sheet.merge_range(bottom_start, start, bottom_start + 5, start + 5, None, )
        sheet.merge_range(bottom_start, start + 7, bottom_start + 5, start + 12, None, )
        bottom_start += 6
        sheet.merge_range(bottom_start, start, bottom_start, start + 5, obj.partner_id.name, center_bold)
        sheet.merge_range(bottom_start, start + 7, bottom_start, start + 12, self.env.user.name, center_bold)
        if start == 0:
            left_bold = wb.add_format({**body_font,'size': 8, 'align': 'left', 'bold': True})
            left_normal = wb.add_format({**body_font, 'size': 7, 'align': 'top'})

            bottom_start += 1
            sheet.merge_range(bottom_start, start, bottom_start, start + 12, 'QUÝ KHÁCH LƯU Ý:', left_bold)

            bottom_start += 1
            sheet.set_row(bottom_start, 20)

            sheet.merge_range(bottom_start, start, bottom_start + 10, start + 12,
                             '1. Trước khi nhận và thanh toán phải kiểm tra kỹ hàng hoá trước khi ra khỏi cửa hàng. '
                             '\nNếu có bất kỳ vấn đề nào trên trang phục/phụ kiện, vui lòng báo ngay cho nhân viên'
                             '\n2. Quý khách vui lòng yêu cầu nhân viên ghi phiếu thu theo đơn và giữ phiếu thu để đối chiếu khi trả hàng.'
                             '\nPhiếu thu có giá trị tương đương với Cam kết/Thoả thuận/Hợp đồng của 2 bên.'
                             '\n3. Quý khách chịu trách nhiệm bảo quản trang phục/phụ kiện trong thời gian thuê kể từ khi ký phiếu thu.'
                             '\n4. Bàn giao trang phục/phụ kiện phải ở trong tình trạng như khi nhận. '
                             '\nMọi vấn đề phát sinh như: hư hỏng, đứt rời 1 phần, rách, sờn vải, thủng lỗ,cháy tàn thuốc, lem màu, '
                             '\nsai khác kiểu dáng ban đầu, vết ố bẩn không đi… dù ở bất cứ vị trí nào trên trang phục/phụ kiện,'
                             '\nhoặc thiếu số lượng nhận ban đầu, '
                             '\nQuý khách vui lòng bồi hoàn 100% giá trị của sản phẩm đó.'
                             '\n5. Trả đúng ngày hẹn ghi trên phiếu. Sau thời gian này sẽ phải trả theo phí quy định của cửa hàng:'
                                  '\t\n- Đối với váy/set trang phục: thanh toán theo combo ngày tiếp theo.'
                                  '\t\n- Đối với phụ kiện: theo giá thuê lẻ.', left_normal)



