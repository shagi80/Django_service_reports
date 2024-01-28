import io
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
from reports.models import ReportsParts


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


def order_part_blank(order_data):

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
