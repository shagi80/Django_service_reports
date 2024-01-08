from django.core.exceptions import ObjectDoesNotExist
import datetime


STATUS_DRAFT = 'draft'
STATUS_SEND = 'send'
STATUS_REFINEMENT = 'refinement'
STATUS_RECEIVED = 'received'
STATUS_VERIFIED = 'verified'
STATUS_ACCEPTED = 'accepted'
STATUS_PAYMENT = 'payment'
STATUS_SEND_AGAIN = 'send_again'

REPORT_STATUS = (
    (STATUS_DRAFT, 'черновик'),
    (STATUS_SEND, 'отправлен на проверку'),
    (STATUS_REFINEMENT, 'на доработке'),
    (STATUS_SEND_AGAIN, 'отправлен повторно'),
    (STATUS_RECEIVED, 'идет проверка'),
    (STATUS_VERIFIED, 'проверка закончена'),
    (STATUS_ACCEPTED, 'принят'),
    (STATUS_PAYMENT, 'передан в оплату')
)

WORKTYPE_PRETRADING = 'pretrading'
WORKTYPE_WARRANTY = 'warranty'


WORKTYPE = (
    (WORKTYPE_PRETRADING, 'предторговый'),
    (WORKTYPE_WARRANTY, 'гарантийный'),
)

FACTORY_NOVATEK = 'K'
FACTORY_NOVASIB = 'N'

FACTORIES = (
    (FACTORY_NOVATEK, 'НОВАТЕК'),
    (FACTORY_NOVASIB, 'НОВАСИБ'),
)


YEAR_CHOICES = []
for r in range(2020, (datetime.datetime.now().year+2)):
    YEAR_CHOICES.append((r, r))

MONTH_CHOICES = ((1, 'январь'), (2, 'февраль'), (3, 'март'), (4, 'аперль'), (5, 'май'), (6, 'июнь'),
                 (7, 'июль'), (8, 'август'), (9, 'сентябрь'), (10, 'октябрь'), (11, 'ноябрь'), (12, 'декабрь'))


PRICE_LITE = 'light'
PRICE_MIDDLE = 'middle'
PRICE_HARD = 'hard'

BASE_PRICE_TYPE = [
    (PRICE_LITE, 'дешевый'),
    (PRICE_MIDDLE, 'средний'),
    (PRICE_HARD, 'дорогой'),
]


def GetBasePriceTitle(key):
    for item in BASE_PRICE_TYPE:
        if item[0] == key:
            return item[1]


#получение расценки за ремонт для конкретного СЦ
def GetPrices(code, center):
    from products.models import Codes, MainProducts, CentersPrices, BasePrice
    result = dict()
    try:
        price = CentersPrices.objects.get(service_center=center, code=code)
        result['individual_price'] = price
        result['price'] = price.price
    except ObjectDoesNotExist:
        try:
            price = BasePrice.objects.get(product=code.product, repair_type=code.repair_type, price_type=center.price_type)
            result['base_price'] = price
            result['price'] = price.price
        except ObjectDoesNotExist:
            pass
    return result


def normalize_string(string):
    sumb_A = ['A', 'А']
    sumb_B = ['B', 'В']
    sumb_C = ['C', 'С']
    sumb_E = ['E', 'Е']
    sumb_H = ['H', 'Н']
    sumb_K = ['K', 'К']
    sumb_P = ['P', 'Р']
    sumb_T = ['T', 'Т']
    sumb_O = ['O', 'О']
    sumb_M = ['M', 'М']
    string = string.upper()
    res = ''
    for sm in string:
        if sm in sumb_A:
            res = res + 'A'
        elif sm in sumb_B:
            res = res + 'B'
        elif sm in sumb_C:
            res = res + 'C'
        elif sm in sumb_E:
            res = res + 'E'
        elif sm in sumb_H:
            res = res + 'H'
        elif sm in sumb_K:
            res = res + 'K'
        elif sm in sumb_P:
            res = res + 'P'
        elif sm in sumb_T:
            res = res + 'T'
        elif sm in sumb_O:
            res = res + 'O'
        elif sm in sumb_M:
            res = res + 'M'
        else:
            res = res + sm
    return res


def parse_serial(model, serial):
    result = {}
    # проверяем первый символ кода
    if not serial[0] in [FACTORY_NOVATEK, FACTORY_NOVASIB]:
        return {'error': 'Первый символ кода не соответствует кодировке производителя !'}
    result['factory'] = serial[0]
    # дольнейшая проверка возможна только если задана кодировка модели
    if not model or not model.code_chars:
        return {'error': 'Невозможно определить модель продукции !'}
    # ищем кодировку модели в номере - она должна найтись со второго символа
    first_char = serial.find(model.code_chars)
    if first_char != 1:
        return {'error': 'Серийный номер не соответствует модели !'}
    # определяем дпту изготовления
    date_str = serial[len(model.code_chars)+1:len(model.code_chars)+7]
    try:
        date = datetime.datetime.strptime(date_str, '%d%m%y').date()
        result['main_date'] = date
        if len(serial) != len(model.code_chars)+11:
            return {'error': 'Длинна серийного номера отличается от необходимой !'}
        # определяем кодировку смены
        if serial[len(model.code_chars)+7] not in ('A', 'B', 'C', 'D', 'E', 'F'):
            return {'error': 'Невозможно определить код смены !'}
        # определяем порядковый номер изделия
        result['shift'] = serial[len(model.code_chars)+7]
        num = serial[len(model.code_chars)+8:]
        if not num.isdigit():
            return {'error': 'Невозможно определить порядковый номер изделий !'}
        # возвращаем результат
        return result
    except ValueError:
        return {'error': 'Невозможно определить дату производства !'}



#--------------------------- ЭКСПОРТ ДАННЫХ ИЗ ФАЙЛОВ ----------------------------------------

#возвращает требуемый формат файла загрузки модели
def datafile_get_format(mod_name):
    if mod_name == 'servicecentres.servicecenters':
        return 'CODE | DESCR | CITY | ADDR | NOTE | POSTADDR | STATUS | ISDEL | FREEPARTS'
    elif mod_name == 'servicecentres.servicecontacts':
        return 'CODE | DESCR | NAME | FUNCT | TEL | EMAIL | SKYPE'
    elif mod_name == 'products.codes':
        return 'CODE | DESCR | ISFOLDER | FOLDER | MAINTYPE'
    else:
        return 'Формат файла не определен ..'


#загружает данные модели из еткстового файла
def datafile_uploaded(f, mod_name):
    from products.models import Codes, MainProducts, CentersPrices, BasePrice
    from servicecentres.models import ServiceCenters, ServiceContacts
    if mod_name == 'servicecentres.servicecenters':
        lines = f.readlines()
        count = 0
        result = []
        for line in lines:
            if count > 0:
                try:
                    line = line.decode('utf-8')
                    data = line.split('|')
                    itm = ServiceCenters()
                    itm.code = data[0].strip()
                    itm.title = data[1]
                    itm.city = data[2]
                    itm.addr = data[3]
                    itm.note = data[4]
                    itm.post_addr = data[5]
                    if data[7] == 'False':
                        itm.is_active = True
                    else:
                        itm.is_active = False
                    if data[8] == 'False':
                        itm.free_parts = False
                    else:
                        itm.free_parts = True
                    itm.save()
                except:
                    result.append(str(count))
            count += 1
        return result
    elif mod_name == 'servicecentres.servicecontacts':
        lines = f.readlines()
        count = 0
        result = []
        for line in lines:
            if count > 0:
                try:
                    line = line.decode('utf-8')
                    data = line.split('|')
                    cnt = ServiceContacts()
                    cnt.service_center = ServiceCenters.objects.get(code=data[0].strip())
                    cnt.name = data[2]
                    cnt.funct = data[3]
                    cnt.tel_num = data[4]
                    cnt.email = data[5]
                    cnt.note = data[6]
                    cnt.save()
                except:
                    result.append(str(count))
            count += 1
        return result
    elif mod_name == 'products.codes':
        lines = f.readlines()
        count = 0
        result = []
        for line in lines:
            if count > 0:
                try:
                    line = line.decode('utf-8')
                    data = line.split('|')
                    code = Codes()
                    code.code = data[0]
                    code.title = data[1]
                    folder = data[3]
                    main_type_pk = int(data[4])
                    if data[2] == '1':
                        is_folder = True
                        code.repair_type = 'none'
                        code.parent = None
                    else:
                        is_folder = False
                        code.repair_type = 'easy'
                        code.parent = Codes.objects.get(product__id=main_type_pk, code=folder, is_folder=True)
                    code.is_folder = is_folder
                    if main_type_pk == 0:
                        code.product = None
                    else:
                        code.product = MainProducts.objects.get(pk=main_type_pk)

                    code.save()
                except:
                    result.append(str(count))
            count += 1
        return result
    else:
        return ['Models not found ..', ]



    # так можно записать большой файл на диск
    #with NamedTemporaryFile(mode='w+b') as dest:
    #    print(dest.name)
    #    print(len(f))
    #    for chunk in f.chunks():
    #        print(chunk)
    #       dest.write(chunk)


