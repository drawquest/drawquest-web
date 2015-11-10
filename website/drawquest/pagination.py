from itertools import dropwhile, takewhile


class Paginator(object):
    def __init__(self, items, per_page, offset='top', direction='next', url=None, min_page_size=None):
        """
        `items` must be a queryset. The results will be ordered by -id.

        `offset` can be an integer, or the string "top".

        `min_page_size` determines how small the page can be before it tries to send back two pages instead of one.
        If `None`, it will default to 1/3 of `per_page`.

        `min_page_size` is currently ignored.
        """
        self.per_page = per_page
        self.offset, self._uncleaned_offset = offset, offset
        self.next_offset = None
        self.previous_offset = None
        self.url = url
        self.direction = direction

        if offset == 'top':
            if self.direction == 'previous':
                raise ValueError("Can't specify both top and previous for direction.")
            self.items = items.order_by('-id')
        elif self.direction == 'next':
            self.items = items.filter(id__lte=self.offset).order_by('-id')
        elif self.direction == 'previous':
            self.items = items.filter(id__gte=self.offset).order_by('id')
        else:
            raise ValueError("Direction must be either next or previous.")

        self.items = self.items[:self.per_page]

        try:
            if direction == 'next':
                oldest_offset_index = -1
                self.offset = self.items[0].id
            else:
                oldest_offset_index = 0
                self.offset = list(self.items)[-1].id

            self.next_offset = list(self.items)[oldest_offset_index].id - 1

            if self._uncleaned_offset != 'top':
                self.previous_offset = self.offset + 1
        except (IndexError, AttributeError,):
            pass

        if direction == 'previous':
            self.items = sorted(self.items, key=lambda item: -item.id)

        if len(self.items) < self.per_page:
            if self.direction == 'next':
                self.next_offset = None
            elif self.direction == 'previous':
                self.previous_offset = None

    def to_client(self, **kwargs):
        ret = {
            'offset': self.offset,
            'direction': self.direction,
        }

        if self.next_offset is not None:
            ret['next'] = self.next_offset
        if self.previous_offset is not None:
            ret['previous'] = self.previous_offset
        if self.url is not None:
            ret['url'] = self.url

        return ret


class FakePaginator(Paginator):
    """
    Implements the same interface as Paginator, but doesn't handle pagination itself
    and its __init__ is slightly different.
    """
    def __init__(self, items, offset='top', next_offset=None, previous_offset=None, direction='next', url=None):
        self.items = items
        self.offset = offset
        self.next_offset = next_offset
        self.previous_offset = previous_offset
        self.direction = direction
        self.url = url

