import sqlite3
import datetime

conn = sqlite3.connect('Count.db')
curr = conn.cursor()

# curr.execute("""DROP TABLE Count_tb""")
#
# curr.execute("""CREATE TABLE Count_tb (
#                 CountID INTEGER PRIMARY KEY,
#                 Timestamp DATE,
#                 EnterCounter INTEGER,
#                 ExitCounter INTEGER
#                 )""")
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
curr.execute("""INSERT INTO Count_tb (Timestamp, EnterCounter,  ExitCounter)
                VALUES (st, EnterCounter, ExitCounter)""")

conn.commit()
conn.close()
