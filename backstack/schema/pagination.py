from math import ceil


class Pagination:
    """Pagination helper returned by :meth:`SQLAlchemyService.paginate_offset`.

    Source: https://github.com/mitsuhiko/flask-sqlalchemy
    """

    def __init__(self, page, per_page, total, items):
        #: the current page number (1 indexed)
        self.page = page
        #: the number of items to be displayed on a page.
        self.per_page = per_page
        #: the total number of items matching the query
        self.total = total
        #: the items for the current page
        self.items = items

    @property
    def metadata(self):
        """http://jsonapi.org/format/#fetching-pagination"""
        return {
            'page_number': self.page,
            'per_page': self.per_page,
            'total_pages': self.pages,
            'total_count': self.total
        }

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    @property
    def prev_num(self):
        """Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1
