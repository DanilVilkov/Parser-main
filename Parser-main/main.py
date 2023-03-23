import io
import re
import numpy as np
import time
from datetime import datetime
from typing import List, Tuple, Any

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


class Operation:
    category = ['Детство', 'Развлечения', 'Зоотовары и услуги',
                'Кино и Театр', 'Косметика', 'Такси', 'Салоны красоты',
                'Транспорт', 'Электроника и Бытовая техника', 'Супермаркеты',
                'Одежда и Обувь', 'АЗС', 'Аптеки', 'Рестораны и кафе', 'Спортивные товары',
                'Перевод с карты', 'Неизвестная категория(+)', 'Здоровье и красота', 'Одежда и аксессуары', 'Все для дома', 'Отдых и развлечения', 'Прочие расходы', 'Прочие операции']

    def __int__(self, date: datetime,
                category: str,
                description: str,
                transaction_amount: float):
        self.date = date
        self.category = category
        self.description = description
        self.transaction_amount = transaction_amount


class DebitSberbank(Operation):
    def __int__(self):
        self.name_card = ''
        self.currency = ''
        self.pre_balance = ''
        self.balance = 0.0
        self.operations = List[Operation]

    def set(self, line: str):
        self.name_card = self.set_name(line)
        self.currency = self.set_currency(line)
        self.balance = self.set_balance(line)
        self.operations = self.set_operations(line)

    def get_console(self):
        print(self.name_card, self.currency, self.balance)
        for i in self.operations:
            print(i.date, i.category, i.description, i.transaction_amount)

    def set_name(self, line: str):
        """
        Sample:
        MIR •••• 9999
        """
        pattern = r'(MIR|Visa|MasterCard|Maestro)(\s\w+)?\s(•{4})\s(\d{4})'
        res = re.search(pattern, line)
        if res:
            print(res.group())
            return res.group()
        else:
            raise error('Имя карты не определено')
        pass

    def set_currency(self, line: str):
        """
        Sample:
        Валюта
        РУБЛЬ РФ
        """
        pattern = r'(Валюта\n(РУБЛЬ РФ)|(ДОЛЛАР США)|ЕВРО)'
        res = re.search(pattern, line)
        if res:
            res = res.group()[7:]
            print(res)
            return res
        else:
            raise error('Валюта не определена')
        pass

    def set_balance(self, line: str) -> float:
        pattern = r'ВСЕГО\sПОПОЛНЕНИЙ\n\n[0-9, \xa0]+\n\n[0-9, \xa0]+'
        res = re.search(pattern, line).group()
        print(res, '|')
        if res:
            pattern = r'[0-9, \xa0]+$'
            res = re.search(pattern, res)
            print(res)
        if res:
            res = res.group()
            temp = convert_to_float(res)
            print(temp)
            return temp
        else:
            error('Баланс не определен')
        pass

    def set_operations(self, line: str) -> List[Operation]:
        date = self.find_datetime(line)

        category, descriptions = self.find_category_and_descriptions(line)

        transaction_amount = self.find_transaction_amount(line)

        operations = self.convert_to_operations(date, category, descriptions, transaction_amount)
        return operations
        pass

    def convert_to_operations(self, date: List[datetime],
                              category: List[str],
                              descriptions: List[str],
                              transaction_amount: List[float]) -> List[Operation]:

        lenght = self.get_lenght(date, category, descriptions, transaction_amount)

        operations = list()
        for i in range(lenght):
            print(date[i], category[i], descriptions[i], transaction_amount[i])
            operation = Operation()
            operation.date = date[i]
            operation.category = category[i]
            operation.description = descriptions[i]
            operation.transaction_amount = transaction_amount[i]
            operations.append(operation)
        return operations
        pass

    def find_datetime(self, line: str) -> List[datetime]:
        pattern = r'[0-9\.]{10}\n[0-9\.]{10}'
        data = re.findall(pattern, line)
        data = [item[-10:] for item in data]

        pattern = r'\d{2}:\d{2}\n'
        cloack = re.findall(pattern, line)
        cloack = [item[:-1] for item in cloack]

        if len(cloack) != len(data):
            raise error("Несоответствие длинна дат и времен (find_datetime)")

        time = [data[i] + ' ' + cloack[i] for i in range(len(data))]
        datetime = self.convert_to_datetime(time)

        return datetime

    def find_category_and_descriptions(self, line: str) -> Tuple[List[str], List[str]]:

        pattern = re.compile(r'[А-Я]{1}[а-я \(\)\+]{2,28}\n[a-zA-Zа-яА-Я\d\.@_ *-:]+', re.I)
        category_and_descriptions = re.findall(pattern, line)
        filtered_category_and_descriptions = category_and_descriptions
        '''filtered_category_and_descriptions = list()
        for item in category_and_descriptions:
            if any(category in item for category in Operation.category):
                filtered_category_and_descriptions.append(item)'''

        category = [item[:item.find('\n')] for item in filtered_category_and_descriptions]
        descriptions = [item[item.find('\n') + 1:] for item in filtered_category_and_descriptions]

        if len(category) != len(descriptions):
            raise error("несоответствее: длинна категорий и описаний (find_category_and_descriptions)")

        return category, descriptions

    def find_transaction_amount(self, line: str) -> List[float]:
        pattern = r'\+?[\d\xa0 ]+,\d{2}'
        cost = re.findall(pattern, line)
        for i in range(len(cost)):
            if cost[i][0] == '+':
                cost[i] = convert_to_float(cost[i])
            else:
                cost[i] = convert_to_float(cost[i], is_negativ=True)

        return cost[5:]

    def get_lenght(self, date: List[datetime],
                   category: List[str],
                   descriptions: List[str],
                   transaction_amount: List[float]) -> int:

        if len(date) != len(category) and len(date) != len(descriptions) and len(date) != len(transaction_amount):
            raise error("Some data is not recognized")

        return len(date)

    def convert_to_datetime(self, time: list()) -> List[datetime]:
        """
        :param time: '15.03.202312:56'
        :return: datetime.datetime(2023, 3, 15, 12, 56)
        """
        return [datetime.strptime(item, '%d.%m.%Y %H:%M') for item in time]


def convert_to_float(line: str, is_negativ=False) -> float:
    try:
        line = line.replace('\xa0', '')
        line = line.replace(' ', '')
        res = float(line.replace(',', '.'))

        if is_negativ:
            res *= -1

        return res
    except:
        error(f'Error in conversation from str to float: {line}')


def error(line: str):
    print(f"Error: {line}")


def extract_text_from_pdf(pdf_path) -> str:
    output_string = io.StringIO()
    with open(pdf_path, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)

    text = output_string.getvalue()
    output_string.close()

    if text:
        return text


if __name__ == '__main__':
    start = time.time()
    debit = DebitSberbank()
    text = extract_text_from_pdf('C:\\Users\\vilko\\Downloads\\Выписка по дебетовой карте (на русском).pdf')
    end = time.time()
    debit.set(text)
    debit.get_console()
    print(text)
    print(format(end - start))

