from itertools import islice, cycle
from typing import List
from pyquery import PyQuery
from .const import CalculationMethod, AsrjuristicMethod


class Item:
    def __init__(self, data: PyQuery, prayers: PyQuery):
        self.date = data('.prayertime-1').eq(0).text()
        items = zip(prayers, data('.prayertime').items())
        self.prayertimes: dict = dict([(k.text(), v.text()) for k, v in items])

    def __repr__(self):
        return f'<Praytime(date={repr(self.date)}, praytimes={self.prayertimes})>'


class Response:

    def __init__(self, data: PyQuery, calcMethod: CalculationMethod, asrjurMethod: AsrjuristicMethod):
        self.origin: PyQuery = data
        self.calculationMethod: str = calcMethod.name
        self.asrjuristicMethod: str = asrjurMethod.name

        prayers = islice(cycle(data('th').items()), 1, None)
        self.raw: List[Item] = [Item(i, prayers)
                                for i in islice(data.items(), 1, None)]
