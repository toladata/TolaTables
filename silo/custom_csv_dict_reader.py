import csv, collections, copy

class CustomDictReader(csv.DictReader):
    '''
        override the next() function and  use an
        ordered dict in order to preserve writing back
        into the file
    '''

    def __init__(self, f, fieldnames = None, restkey = None, restval = None, dialect ="excel", *args, **kwds):
        csv.DictReader.__init__(self, f, fieldnames = None, restkey = None, restval = None, dialect = "excel", *args, **kwds)

    def next(self):
        if self.line_num == 0:
            # Used only for its side effect.
            self.fieldnames
        row = self.reader.next()
        self.line_num = self.reader.line_num

        # unlike the basic reader, we prefer not to return blanks,
        # because we will typically wind up with a dict full of None
        # values
        while row == []:
            row = self.reader.next()
        d = collections.OrderedDict(zip(self.fieldnames, row))

        lf = len(self.fieldnames)
        lr = len(row)
        if lf < lr:
            d[self.restkey] = row[lf:]
        elif lf > lr:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d
