#!/usr/bin/env python3
# coding: utf8


from flask import Flask, render_template, abort, Response, send_from_directory

from os import listdir
from os.path import isfile, join

from datetime import datetime

import json
import re
import unidecode
import markdown

app = Flask(__name__)

def parseDate(datetimeString):
    if datetimeString == "":
        return None
    try: 
        date = datetime.strptime(datetimeString.strip(),"%Y-%m-%d %H:%M")
    except ValueError:
        try : 
            date = datetime.strptime(datetimeString.strip(),"%Y-%m-%d")
        except ValueError:
            date = datetime.strptime(datetimeString.strip(),"%Y-%m-%d %H:%M:%S")
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
        
        #Content and not header
        self.content = markdown.markdown(postContent)
        cleanr = re.compile('<.*?>')
        self.excerpt = re.sub(cleanr, '',markdown.markdown(' '.join(postContent.split()[:40]) + "..."))

def getIndex(start=0,number=10):
    jsonFile = open("contentData.json", "r")
    data = json.load(jsonFile);
    jsonFile.close()
    if start>=len(data['posts']):
        return ([],False,True)
    #Get offset to hide not yet published posts
    offset=0
    while(parseDate(data['posts'][offset]['date']) > datetime.now() and offset<len(data['posts'])):
        offset+=1
    start += offset
    if start>=len(data['posts']):
        return ([],False,True)
    indexData = []
    for post in data['posts'][start:start+number]:
        indexData.append(Post(post['file']))
    return (indexData,start == offset,indexData[-1].file == data['posts'][-1]['file'])

def getPostIdByUrl(url,draft=False):
    jsonFile = open("contentData.json", "r")
    data = json.load(jsonFile);
    jsonFile.close()
    if draft:
        postList='drafts'
    else:
        postList='posts'
    for id,post in enumerate(data[postList]):
        if post['url'] == url:
            return id;
    return -1

def getPostByUrl(url):
    jsonFile = open("contentData.json", "r")
    data = json.load(jsonFile);
    jsonFile.close()
    for id,post in enumerate(data['posts']):
        if post['url'] == url:
            return Post(post['file']);
    for id,post in enumerate(data['drafts']):
        if post['url'] == url:
            return Post(post['file']);
    return None

def getPostsByTag(tag):
    jsonFile = open("contentData.json", "r")
    data = json.load(jsonFile);
    jsonFile.close()
    posts = []
    for url in data['tags'][tag]:
        posts.append(getPostByUrl(url))
    return posts

def getPostById(postId,draft=False):
    if postId < 0:
        return None
    jsonFile = open("contentData.json", "r")
    data = json.load(jsonFile);
    jsonFile.close()
    if draft:
        postList="drafts"
    else:
        postList="posts"
    if postId >= len(data[postList]):
        return None
    return Post(data[postList][postId]['file']);

###############################################################################
####################                Filters                ####################
###############################################################################

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    return value.strftime(format)

###############################################################################
####################                Refresh                ####################
###############################################################################

@app.route('/refresh/<key>')
def refresh(key=None):
    keyFile = open('refresh.key','r')
    goodKey = keyFile.read().splitlines()[0]
    keyFile.close()
    if key==None or key!=goodKey:
        abort(404)
    files = [join('posts',f) for f in listdir('posts') if isfile(join('posts', f))]
    posts=[]
    for postFile in files:
        posts.append(Post(postFile))

    posts.sort(key=lambda p: p.position)
    posts.sort(key=lambda p: p.date,reverse=True)

    tags={}
    shortPublicPosts=[]
    shortDraftPosts=[]
    for post in posts:
        if post.status == 'public':
            for tag in post.tags:
                if tag in tags:
                    tags[tag].append(post.url)
                else:
                    tags[tag] = [post.url]
            shortPublicPosts.append({
                'date':post.date,
                'title': post.title,
                'status':post.status,
                'author':post.author,
                'tags':post.tags,
                'file':post.file,
                'url':post.url
            })
        else:
            shortDraftPosts.append({
                'date':post.date,
                'title': post.title,
                'status':post.status,
                'author':post.author,
                'tags':post.tags,
                'file':post.file,
                'url':post.url
            })


    jsonFile = open("contentData.json", "w")
    json.dump({"posts":shortPublicPosts,"drafts":shortDraftPosts,"tags":tags}, jsonFile, default=str)
    jsonFile.close()
    js = json.dumps({"success":True,"posts":{"total":len(posts),"public":len(shortPublicPosts),"drafts":len(shortDraftPosts)},"tags":len(tags)})
    resp = Response(js, status=200, mimetype='application/json')
    return resp

###############################################################################
####################                 Index                 ####################
###############################################################################

@app.route('/')
@app.route('/page/<page>')
def index(page=1):
    postsPerPage=10
    page=int(page)
    posts,isFirst,isLast = getIndex((page-1)*postsPerPage,postsPerPage)
    return render_template('index.html',posts=posts,page=page,isFirst=isFirst,isLast=isLast)

@app.route('/post/<url>')
def post(url):
    postId = getPostIdByUrl(url)
    if postId == -1:
        abort(404)
    post = getPostById(postId)
    oldPost = getPostById(postId+1)
    newPost = getPostById(postId-1)
    return render_template('post.html', post=post, oldPost=oldPost, newPost=newPost)

@app.route('/draft/<url>')
def draft(url):
    postId = getPostIdByUrl(url,draft=True)
    if postId == -1:
        abort(404)
    post = getPostById(postId,draft=True)
    return render_template('post.html', post=post)

@app.route('/tag/<tag>')
def tag(tag):
    posts=getPostsByTag(tag)
    return render_template('tags.html', posts=posts, tag=tag)

@app.route('/img/<img>')
def img(img):
    return send_from_directory("posts/img",img);

