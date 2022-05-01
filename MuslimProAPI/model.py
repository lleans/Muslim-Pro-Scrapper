from typing import List
from pyquery import PyQuery

class Item:
    def __init__(self, data: PyQuery):
        self.origin: PyQuery = data
        self.prayers: str = data('p').eq(0).text()
        self.praytime: str = data('p').eq(1).text()

    def __repr__(self):
        return f'<Praytime(prayers={repr(self.prayers)}, praytime={self.praytime})>'

class Response:
    def __init__(self, data: PyQuery):
        self.origin:PyQuery = data
        self.raw: List[Item] = [Item(i) for i in data.items()]