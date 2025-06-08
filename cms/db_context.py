class DbContext:
    """Mimic an Entity Framework style DbContext using in-memory stores."""

    def __init__(self):
        self.contents = {}
        self.categories = {}
        self.tokens = {}
