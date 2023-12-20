from threading import Thread
import subprocess
import time
import sqlite3
import os

#db folder
database_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database')
if not os.path.exists(database_folder):
    os.mkdir(database_folder)

#create db
db_path = os.path.join(database_folder, 'players.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_links (
        discord_id INTEGER PRIMARY KEY,
        steam_id64 INTEGER
    )
''')
conn.commit()
conn.close()

# Start the Flask app
def run_flask_app():
    subprocess.run(["python", "flask_app.py"])

# Start the Discord bot
def run_discord_bot():
    subprocess.run(["python", "discord_bot.py"])

if __name__ == '__main__':
    # Start Flask app in a separate thread
    flask_thread = Thread(target=run_flask_app)
    flask_thread.start()

    # Allow some time for the Flask app to start before starting the Discord bot
    time.sleep(2)

    # Start Discord bot
    run_discord_bot()
