import io
import xlwt
import os.path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    PageTemplate,
    NextPageTemplate,
    Table,
    Paragraph,
    Image,
    TableStyle,
    Frame,
    PageBreak,
    Spacer
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportssite.settings import STATIC_ROOT, STATICFILES_DIRS
from servicecentres.models import ServiceCenters
from reports.models import ReportsParts, ReportsRecords


def order_part_blank(order_data):
    """ Формирование этикеток заказа деталей в pdf. """

    def registrer_arial():
        """Регистрация TrueType кирилического шрифта."""

        pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
        pdfmetrics.registerFont(TTFont('ArialBd', 'ArialBd.ttf'))

    def PageHeader(canvas, doc):
        canvas.saveState()

        header_title = ParagraphStyle(
            'h4',
            fontName='ArialBd',
            fontSize=12,
            alignment=0,
            spaceAfter=2
        )
        header_data = ParagraphStyle(
            'p',
            fontName='Arial',
            fontSize=10,
            alignment=0,
        )

        logo_file = (
            f'{STATICFILES_DIRS[0]}/icons/tm.png'
            if os.path.exists(f'{STATICFILES_DIRS[0]}/icons/tm.png')
            else f'{STATIC_ROOT}/icons/tm.png'
        )
        logo = Image(logo_file)
        logo.drawHeight = 70*mm*logo.drawHeight / logo.drawWidth
        logo.drawWidth = 70*mm

        supplier_title = Paragraph('ИП Атаманчук А.В.', header_title)
        supplier_addr = Paragraph(
            '''
            Россия, 184430, Мурманская обл, Печенгский,
            г.Заполярный, ул.Юбилейная, д.2, кв.184
            ''',
            header_data
            )
        supplier_contact = Paragraph(
            '8-800-200-46-36',
            header_data
        )

        title_table = Table(
            [
                [logo, [supplier_title, supplier_addr, supplier_contact]]
            ],
            colWidths=[80 * mm, 90 * mm],
        )
        title_table.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]
            )
        )

        story = []
        story.append(title_table)
        f = Frame(20*mm, 257*mm, 170*mm, 30*mm, showBoundary=0)
        f.addFromList(story, canvas)

        canvas.restoreState()

    # регистрируем кириллический шриф
    registrer_arial()

    header_4 = ParagraphStyle(
        'h4',
        fontName='ArialBd',
        fontSize=14,
        alignment=0,
        spaceAfter=5
    )
    header_5 = ParagraphStyle(
        'h5',
        fontName='ArialBd',
        fontSize=12,
        alignment=0,
        spaceAfter=2,
    )
    header_table = ParagraphStyle(
        'header_table',
        fontName='ArialBd',
        fontSize=10,
        alignment=1,
    )
    paradraph = ParagraphStyle(
        'p',
        fontName='Arial',
        fontSize=12,
        alignment=0,
        spaceAfter=1
    )

    # формируем документ
    buffer = io.BytesIO()
    margin = 20 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title='renova_ordes',
        author='renova-service.ru',
    )

    # создаем шаблон страницы с одним фремом на всю страницу
    frame = Frame(margin, margin, doc.width, doc.height, id='frame')
    portrait_template = PageTemplate(
        id='portrait',
        frames=[frame],
        pagesize=A4,
        onPage=PageHeader,
    )

    # добавляем шаблон в документ, формируем документ
    doc.addPageTemplates([portrait_template])
    elements = []
    for order in order_data:
        # подготовка информации о сервисном центре
        center = ServiceCenters.objects.get(pk=order['center'])
        center_title = Paragraph(
            center.title,
            header_4
        )
        center_addr = Paragraph(
            center.post_addr,
            paradraph
        )
        contact = center.servicecontacts_set.all().values_list(
            'name', 'tel_num', 'email'
            )
        contact_title = Paragraph(
            ', '.join(contact.first()) if contact else center.user.email,
            paradraph
            )
        center_table = Table(
            [
                [
                    Paragraph('Сервисный центр:', header_5),
                    [center_title, center_addr]
                ],
                [
                    Paragraph('Контактное лицо:', header_5),
                    [contact_title]
                ],
            ],
            colWidths=[50 * mm, 120 * mm],
        )
        center_table.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]
            )
        )
        elements.append(Spacer(0, 20*mm))
        elements.append(center_table)

        # подготовка информации о деталях
        elements.append(Spacer(0, 5*mm))
        part_data = [
                [
                    Paragraph('№', header_table),
                    Paragraph('Наименование', header_table),
                    Paragraph('Кол', header_table)
                ],
            ]
        parts = ReportsParts.objects.filter(pk__in=order['parts'])
        cnt = 1
        for part in parts:
            part_data.append(
                [
                    Paragraph(str(cnt), paradraph),
                    [
                        Paragraph(part.title, paradraph),
                        Paragraph(
                            (
                                f'({part.record.model_description}, '
                                f'ремонт №{part.record.pk} из отчета '
                                f'за {part.record.report.get_report_month()})'
                            ),
                            paradraph
                        ),
                    ],
                    Paragraph(str(part.count), paradraph)
                ],
            )
            cnt += 1
        part_table = Table(part_data, colWidths=[10*mm, 140*mm, 15*mm])
        part_table.setStyle(
            TableStyle(
                [
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.silver),
                ]
            )
        )
        elements.append(part_table)

        # информация о менеджере
        elements.append(Spacer(0, 10*mm))
        mager_table = Table(
            [
                [
                    Paragraph('Отвественный за отправку: ', header_5),
                    [
                        Paragraph(str(center.region.staff_user), paradraph),
                        Paragraph(center.region.staff_user.email, paradraph)
                    ]
                ]

            ],
            colWidths=[70*mm, 100*mm]
        )
        mager_table.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]
            )
        )
        elements.append(mager_table)

        # разрыв страницы
        elements.append(NextPageTemplate('portrait'))
        elements.append(PageBreak())

    doc.build(elements)

    return buffer


def report_xls(report):
    """ Формирование выгрузки отчета в xls """

    report_date = report.get_report_month()
    workBook = xlwt.Workbook(encoding='utf-8')
    workSheet = workBook.add_sheet(report_date)

    # Sheet header, first row
    boldStyle = xlwt.XFStyle()
    boldStyle.font.bold = True
    row_num = 0
    workSheet.write(
        row_num,
        0,
        f'Статистическая таблица за {report_date}. {report.service_center}',
        boldStyle,
    )

    # Table header, third row
    row_num = 2
    workSheet.row(row_num).height = 600
    headerStyle = xlwt.easyxf(
        'font: bold off, color black; borders: left thin, right thin,\
              top thin, bottom thin;  pattern: pattern solid, fore_color\
                  white, fore_colour gray25; align: horiz center, vert top;'
    )
    headerStyle.alignment.wrap = 1
    columns = [
        '№',
        'Клиент',
        'Адрес',
        'Телефон',
        'Модель',
        'Серийный номер',
        'Дата продажи',
        'Дата приема',
        'Дата ремонта',
        'Описание датали',
        'Цена детали',
        'Кол-во штук',
        'Номер накладной',
        'Выезд',
        'За работы',
        'Заявленный дефект',
        'Описание работ',
        'Код неисправности',
    ]
    for col_num in range(len(columns)):
        workSheet.write(row_num, col_num, columns[col_num], headerStyle)

    # Sheet body, remaining rows
    style = xlwt.XFStyle()
    records = ReportsRecords.objects.filter(report=report)
    row_num_str = 0
    for record in records:
        row_num += 1
        row_num_str += 1
        workSheet.col(0).width = 1000
        workSheet.write(row_num, 0, str(row_num_str), style)
        workSheet.col(1).width = 5000
        workSheet.write(row_num, 1, record.client, style)
        workSheet.write(row_num, 2, record.client_addr, style)
        workSheet.write(row_num, 3, record.client_phone, style)
        workSheet.col(4).width = 5000
        workSheet.write(row_num, 4, record.model_description, style)
        workSheet.col(5).width = 5000
        workSheet.write(row_num, 5, record.serial_number, style)
        if record.buy_date:
            workSheet.write(
                row_num, 6, record.buy_date.strftime('%d.%m.%y'), style
            )
        if record.start_date:
            workSheet.write(
                row_num, 7, record.start_date.strftime('%d.%m.%y'), style
            )
        if record.end_date:
            workSheet.write(
                row_num, 8, record.end_date.strftime('%d.%m.%y'), style
            )
        if record.move_cost:
            workSheet.write(row_num, 13, record.move_cost, style)
        if record.work_cost:
            workSheet.write(row_num, 14, record.work_cost, style)
        workSheet.col(15).width = 8000
        workSheet.write(row_num, 15, record.problem_description, style)
        workSheet.col(16).width = 8000
        workSheet.write(row_num, 16, record.work_description, style)
        workSheet.col(17).width = 2000
        workSheet.write(row_num, 17, record.code.code, style)
        parts = ReportsParts.objects.filter(record=record)
        for part in parts:
            workSheet.col(9).width = 8000
            workSheet.write(row_num, 9, part.title, style)
            if part.price:
                workSheet.write(row_num, 10, part.price, style)
            if part.count:
                workSheet.write(row_num, 11, part.count, style)
            workSheet.write(row_num, 12, part.document, style)
            row_num += 1
        if parts:
            row_num -= 1

    # Footer
    row_num += 1
    workSheet.write(row_num, 10, f'{report.total_part} руб', boldStyle)
    workSheet.write(row_num, 13, f'{report.total_move} руб', boldStyle)
    workSheet.write(row_num, 14, f'{report.total_work} руб', boldStyle)
    workSheet.write(
        row_num + 1,
        0,
        f'Всего по отчету: {report.total_cost} рублей.',
        boldStyle,
    )

    return workBook
