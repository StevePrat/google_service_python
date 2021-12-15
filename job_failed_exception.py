from typing import Iterable

class JobFailedException(Exception):
    failed_items_list = []

    def __init__(self, failed_items: Iterable) -> None:
        self.failed_items_list = list(failed_items)
    
    def __str__(self) -> str:
        return 'The following items are not completed:\n' + '\n'.join(str(i) for i in self.failed_items_list) + '\n'
