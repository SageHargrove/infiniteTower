import sys; sys.path.append('.'); from database import db
with db() as conn:
    conn.execute('UPDATE facilities SET type = "Training Grounds" WHERE type = "Training Center"')

