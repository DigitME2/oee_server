import sqlalchemy

engine = sqlalchemy.create_engine("sqlite:///test.db")


mylist = {"one":"un", "two":"deux"}

if mylist["three"] == "un":
    print("True")