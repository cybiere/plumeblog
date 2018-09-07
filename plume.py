#!/usr/bin/env python3
# coding: utf8


from flask import Flask
from flask import render_template
from flask import abort

from os import listdir
from os.path import isfile, join

from datetime import datetime

app = Flask(__name__)

###############################################################################
####################                Refresh                ####################
###############################################################################

def parseDate(datetimeString):
    if datetimeString == "":
        return None
    try: 
        date = datetime.strptime(datetimeString.strip(),"%Y-%m-%d %H:%M")
    except ValueError:
        date = datetime.strptime(datetimeString.strip(),"%Y-%m-%d")
    return date

class Post:
    def __init__(self,postFilePath=None):
        attributes = {
                'title': lambda self,val: setattr(self,'title',val.strip()),
                'author': lambda self,val: setattr(self,'author',val.strip()),
                'date': lambda self,val: setattr(self,'date',parseDate(val.strip()))
        }

        for key, value in attributes.items():
            value(self,"")
        if postFilePath==None:
            return

        try:
            postFile = open(postFilePath,"r", encoding="utf-8")
        except:
            print('Open post file {} failed.',postFilePath)
            raise ValueError
        postFileContent = postFile.read()
        postFile.close()
        postHeader,postContent = postFileContent.split('\n\n',maxsplit=1)
        headers = postHeader.splitlines()
        for header in headers:
            key,value = header.split(':',maxsplit=1)
            key=key.strip().lower()
            if key in attributes:
                attributes[key](self,val=value)


@app.route('/refresh/<key>')
def refresh(key=None):
    if key==None or key!="maclef":
        abort(404)
    files = [join('posts',f) for f in listdir('posts') if isfile(join('posts', f))]
    posts=[]
    for post in files:
        posts.append(Post(post))

    posts.sort(key=lambda p: p.date,reverse=True)

    titles= []
    for post in posts:
        titles.append(post.date.strftime("%Y-%m-%d %H:%M") + " - " + post.title + " - " + post.author)
    return "<br />".join(titles)

###############################################################################
####################                 Index                 ####################
###############################################################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)


