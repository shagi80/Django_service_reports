""" представления почтовых сообщений """
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from reportssite.settings import DEBUG


def mail_ordered_parts(record, parts):
    """ уведомление менеджера о заказе запчастей """

    # формируем список получателей
    mails = ['shagi80@mail.ru', ] if DEBUG else [record.report.service_center.region.staff_user.email, ]
    # если есть кому отправлять формируем письмо
    if mails:
        # рендеринг HTML шаблона
        html_content = render_to_string(
                'mail/parts_order.html',
                {'record': record, 'parts': parts,}
            )
        # подготовка сообщения
        msg = EmailMultiAlternatives(
                subject = f'RENOVA. Заказа на запчасти от {record.report.service_center}',
                body =  f'RENOVA. Заказа на запчасти от {record.report.service_center}',
                from_email = 'report_service@re-nova.com',
                to = mails
            )                
        # привязка HTML и отправка
        msg.attach_alternative(html_content, "text/html")
        msg.send()    
        return True
    
    return False        


def mail_send_parts(parts):
    """ уведомление СЦ об отправке запчастей """

    # формируем список получателей
    mails = ['shagi80@mail.ru'] if DEBUG else [parts.first().record.report.service_center.user.email, ]
    # если есть кому отправлять формируем письмо
    if mails:
        # рендеринг HTML шаблона
        html_content = render_to_string(
                'mail/parts_send.html',
                {'parts': parts,}
            )
        # подготовка сообщения
        msg = EmailMultiAlternatives(
                subject = f'RENOVA. Ваш заказ на запчасти отправлен.',
                body =  f'RENOVA. Ваш заказ на запчасти отправлен.',
                from_email = 'report_service@re-nova.com',
                to = mails
                #to = ['shagi80@mail.ru']
            )                
        # привязка HTML и отправка
        msg.attach_alternative(html_content, "text/html")
        msg.send()    
        return True
    
    return False        


def mail_message_for_center(center, subject, title, message):
    """ произвольое уведомление сервиса с текстом """

    # формируем список получателей
    mails = ['shagi80@mail.ru'] if DEBUG else [center.user.email, ]
    # если есть кому отправлять формируем письмо
    if mails:
        # рендеринг HTML шаблона
        html_content = render_to_string(
                'mail/message_for_center.html',
                {'title': title, 'message': message, }
            )
        # подготовка сообщения
        msg = EmailMultiAlternatives(
                subject = f'RENOVA.{subject}.',
                body =  f'RENOVA. {title}.',
                from_email = 'report_service@re-nova.com',
                to = mails
            )                
        # привязка HTML и отправка
        msg.attach_alternative(html_content, "text/html")
        msg.send()    
        return True

    return False        


def mail_message_for_staff(center, subject, title, message):
    """ произвольое уведомление менеджера с текстом """

    # формируем список получателей
    mails = ['shagi80@mail.ru'] if DEBUG else [center.staff_user.email, ]
    # если есть кому отправлять формируем письмо
    if mails:
        # рендеринг HTML шаблона
        html_content = render_to_string(
                'mail/message_for_center.html',
                {'title': title, 'message': message, }
            )
        # подготовка сообщения
        msg = EmailMultiAlternatives(
                subject = f'RENOVA.{subject}.',
                body =  f'RENOVA. {title}.',
                from_email = 'report_service@re-nova.com',
                to = mails
            )                
        # привязка HTML и отправка
        msg.attach_alternative(html_content, "text/html")
        msg.send()    
        return True

    return False 


def mail_new_acts(last_date, acts):
    """ уведомление менеджероd о новых вктах НРП"""

    # формируем список получателей
    mails = []
    if DEBUG:
        mails.append('shagi80@mail.ru')
    else:
        users = User.objects.filter(is_active=True, is_staff=True, email__isnull=False)
        for user in users:
            mails.append(user.email)
    # если есть кому отправлять формируем письмо
    if mails:
        # рендеринг HTML шаблона
        html_content = render_to_string(
                'mail/new_acts.html',
                {'acts': acts, 'last_date': last_date}
            )
        # подготовка сообщения
        msg = EmailMultiAlternatives(
                subject = f'RENOVA. Новые акты неремонтопригодности.',
                body =  f'RENOVA. Новые акты неремонтопригодности.',
                from_email = 'report_service@re-nova.com',
                to = mails
            )                
        # привязка HTML и отправка
        msg.attach_alternative(html_content, "text/html")
        msg.send()    
        return True

    return False
