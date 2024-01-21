"""Функции формирования PDF документов."""
import io
import qrcode
from django.urls import reverse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    Paragraph,
    Image,
    TableStyle,
)
from reportlab.graphics import shapes

from reportssite.settings import MEDIA_ROOT, STATIC_ROOT


def registrer_arial():
    """Регистрация TrueType кирилического шрифта."""

    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    pdfmetrics.registerFont(TTFont('ArialBd', 'ArialBd.ttf'))


def create_QR(pk):
    """Генерация QR кода."""

    path = f'{MEDIA_ROOT}/act_qrcode/qr{pk}.png'
    code = f'https://renova-service.ru{reverse("act-check", args=[pk])}'
    img = qrcode.make(code)
    img.save(path)
    return path


def prepare_pdf(act):
    """Акт неремонтопригодности для СЦ."""

    # регистрируем кириллический шрифт
    registrer_arial()

    # определяем стили обзацеы
    styleTitle = ParagraphStyle(
        'Title',
        fontName='ArialBd',
        fontSize=16,
        alignment=1,
    )
    styleTMain = ParagraphStyle(
        'Title',
        fontName='Arial',
        fontSize=12,
    )
    styleTMainBd = ParagraphStyle(
        'Title',
        fontName='ArialBd',
        fontSize=12,
    )

    # верхний рисунок
    image = Image(f'{MEDIA_ROOT}/act_qrcode/tm.png')
    image.drawHeight = 25 * mm
    image.drawWidth = 170 * mm

    # формируем заголовок
    qcode = Image(create_QR(act.pk))
    qcode.drawHeight = 40 * mm * qcode.drawHeight / qcode.drawWidth
    qcode.drawWidth = 40 * mm

    title_table = Table(
        [
            [Paragraph('АКТ НЕРЕМОНТОПРИГОДНОСТИ', styleTitle), qcode],
            [
                Paragraph(
                    f'{act.pk} от {act.doc_date.strftime("%d.%m.%Y")}',
                    styleTitle,
                ),
                '',
            ],
            ['', ''],
            [Paragraph(f'{act.status.get_status_display()}', styleTitle), ''],
            [
                Paragraph(
                    f'{act.status.created_at.strftime("%d.%m.%Y")}', styleTitle
                ),
                '',
            ],
            ['', ''],
        ],
        colWidths=[130 * mm, 40 * mm],
    )
    title_table.setStyle(
        TableStyle(
            [
                ('SPAN', (1, 0), (1, -1)),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
            ]
        )
    )

    # заполняем данные таблицы, формируем таблицу
    data = []

    def add_row(col1, col2):
        col2 = col2 if col2 else '-----'
        data.append(
            [
                Paragraph(col1, style=styleTMainBd),
                Paragraph(col2, style=styleTMain),
            ]
        )

    if act.product:
        add_row('Вид продукции:', act.product.title)
    if act.model:
        add_row('Модель:', act.model_description)
    add_row('Серийный номер:', act.serial_number)
    add_row('Сервисный центр:', act.center.title)
    add_row('', f'адрес: {act.center.addr}')
    if act.work_type == 'warranty' or act.client:
        if act.client_type == 'organization':
            add_row('Владелец:', 'организация')
            add_row('', f'наименование: {act.client}')
            if act.client_email:
                add_row('', f'e-mail: {act.client_email}')
        else:
            add_row('Владелец:', act.client)
        add_row('', f'адрес: {act.client_addr}')
        add_row('', f'тел: {act.client_phone}')
    else:
        add_row('Владелец:', 'нет (предторговое обращение продавца)')
    if act.work_type == 'warranty':
        add_row('Дата продажи:', act.buy_date.strftime('%d %m %Y'))
    add_row('Продавец:', act.shop)
    add_row('', f'адрес: {act.shop_addr}')
    add_row('', f'тел: {act.shop_phone}')
    if act.receipt_date:
        add_row(
            'Дата поступления в ремонт:', act.receipt_date.strftime('%d %m %Y')
        )
    add_row('Комплектность:', act.completeness)
    add_row('Заявленная неисправность:', act.problem_description)
    add_row('Выявленная неиспраность:', act.work_description)
    if act.code:
        add_row('Код неисправности:', f'{act.code.code}. {act.code.title}')
    add_row('Заключение:', act.decree)
    # add_row('Примечание:', act.note)

    main_table = Table(data, colWidths=[70 * mm, 100 * mm])
    main_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONT', (0, 0), (-1, -1), 'Arial'),
                ('FONT', (0, 0), (0, -1), 'ArialBd'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]
        )
    )

    # пробельная линия
    line = shapes.Drawing(0, 14 * mm)
    line.add(shapes.Line(0, 7 * mm, 160 * mm, 7 * mm))

    # формируем документ
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=20 * mm,
        topMargin=5 * mm,
        bottomMargin=20 * mm,
        title=f'renova_nrp_{act.pk}',
        author='renova-service.ru',
    )
    elements = []
    elements.append(image)
    elements.append(title_table)
    elements.append(line)
    elements.append(main_table)
    elements.append(line)
    if act.device_location:
        elements.append(
            Paragraph(
                f'Изделие {act.get_device_location_display()}.', styleTitle
            )
        )
    doc.build(elements)

    return buffer
