import database
database.set_profile('main')
from database import db
with db() as conn:
    rows = conn.execute("SELECT id, name, level, hero_class, hidden_class FROM heroes WHERE hero_class = 'Adventurer'").fetchall()
    print('heroes with hero_class=Adventurer:', len(rows))
    if len(rows) > 0:
        conn.execute("UPDATE heroes SET hero_class = 'Classless' WHERE hero_class = 'Adventurer'")
        print('Updated heroes to Classless')
