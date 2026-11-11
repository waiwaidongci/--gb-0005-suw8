from sqlalchemy.inspection import inspect
def record(row):
    return {c.key: getattr(row,c.key) for c in inspect(row).mapper.column_attrs}
