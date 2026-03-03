import sqlite3
conn = sqlite3.connect(r'd:\newrecomandationsystem\data\news.db')
conn.execute("DELETE FROM News WHERE category='TRANG CHỦ'")
conn.commit()
print('Deleted TRANG CHU articles')
conn.close()
