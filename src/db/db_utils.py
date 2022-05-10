class DBUtils:
    def __init__(self):
        self.transactions = None
        self.base = None
        self.blocks = None
        self.future = None

    def get_transactions(self):
        return self.transactions

    def get_blocks(self):
        return self.blocks

    def get_future(self):
        return self.future

    def set_tables(self, transactions, blocks, future):
        self.transactions = transactions
        self.blocks = blocks
        self.future = future

    def set_base(self, base):
        self.base = base


db_utils = DBUtils()
