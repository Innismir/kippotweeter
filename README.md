kippotweeter
============

Python script that monitors a Kippo log file and sends alerts to Twitter

Prequisites
-------------------------

Kippo (natch) & SQLite3


Setup
-------------------------
Clone the Github repository

    cat kippotweeter.sql | sqlite3 kippotweeter.db

Edit your config.ini with your Node Name (used for tweets), the location of the kippotweeter.db file, the location of the Kippo log file, and finally Twitter OAuth Application Name, Consumer Secret, and Consumer Key. 

Run the program for the first time:
    ./kippotweeter.py

Follow the prompts on screen to authorize kippotweeter to your Twitter account. Once this is done, hit "Ctrl-C" to exit.
Run it again with nohup:
    nohup ./kippotweeter.py &

Done!
