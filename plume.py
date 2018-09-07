#!/usr/bin/env python3
# coding: utf8


from flask import Flask, render_template, abort, Response

from os import listdir
from os.path import isfile, join

from datetime import datetime

import json
import re
import unidecode

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
                'date': lambda self,val: setattr(self,'date',parseDate(val.strip())),
                'title': lambda self,val: setattr(self,'title',val.strip()),
                'status': lambda self,val: setattr(self,'status',val.strip()),
                'author': lambda self,val: setattr(self,'author',val.strip()),
                'tags': lambda self,val: setattr(self,'tags',val.strip().split(' ')),
                'position': lambda self,val: setattr(self,'position',val.strip()),
                'file': lambda self,val: setattr(self,'file',val.strip()),
                'url': lambda self,val: setattr(self,'url',val.strip()),
        }

        for key, value in attributes.items():
            value(self,"")
        if postFilePath==None:
            return

        try:
            postFile = open(postFilePath,"r", encoding="utf-8")
        except:
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
        attributes['file'](self,postFilePath)
        
        if self.position == "":
            self.position = "0";
        if self.url == "":
            _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')
            result = []
            for word in _punct_re.split(self.title.lower()):
                result.append(unidecode.unidecode(word))
            self.url = "-".join(result)
        if "" in self.tags:
            self.tags.remove("")
        
        self.excerpt = ' '.join(postContent.split()[:40]) + "..."


@app.route('/refresh/<key>')
def refresh(key=None):
    if key==None or key!="maclef":
        abort(404)
    files = [join('posts',f) for f in listdir('posts') if isfile(join('posts', f))]
    posts=[]
    for post in files:
        posts.append(Post(post))

    posts.sort(key=lambda p: p.position)
    posts.sort(key=lambda p: p.date,reverse=True)

    tags={}
    for post in posts:
        for tag in post.tags:
            if tag in tags:
                tags[tag].append(post.url)
            else:
                tags[tag] = [post.url]

    js = json.dumps([[post.__dict__ for post in posts],tags], default=str)
    resp = Response(js, status=200, mimetype='application/json')
    return resp

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


