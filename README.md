# PopulusBot

Populus bot is a new way to automaticaly leave comments and share information on populus-veiwer.
the idea is simple, you feed populus bot words to look for + plus some revant information (links or defiitions)
and populus bot leaves a comment with that relevent info on every page those words

### To set up and use PopulusBot is easy, but requires a little of configuring
1. go to configuration.yaml and put in the mxid and password of the bot that you would
like to use
2. create a JSON file with __key, value__ pairs that represent __your search terms, relevant information__. I have setup.json here as an example but you can use whatever you want
3. under skills -> setup, set the file path of your JSON file
4. you can add additional __find__ skills simply by adding new entries under skills with ./skils.find.py as the path
```
{my-skill-name}:
    path: ./skills/find.py <- this stays the sane
    setup: {file path}
```
