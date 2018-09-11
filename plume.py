#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### Plume is a simple semi-static blog engine using Flask
### https://github.com/ncosnard/plumeblog

from flask import Flask, render_template, abort, Response, send_from_directory

from os import listdir
from os.path import isfile, join

from datetime import datetime

import json
import re
import unidecode
import markdown

app = Flask(__name__)

####################################################
# Utilities
####################################################

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    return value.strftime(format)

def parseDate(datetimeString):
    # Transforms dates from string to datetime object
    # Raises ValueError if no format is recognized
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

####################################################
# Classes definition
####################################################

class Post:
    # Post object allows storing a post from a file as a structured object with additionnal info (excerpt, markdown interpretation...
    def __init__(self,postFilePath):
        #TODO No use to load/interpret content for refresh only ?
        #TODO Handle wrongly formatted posts gracefully
        if postFilePath==None:
            raise ValueError
        
        #Switch-case like structure to parse post headers
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
        
        #Init to empty
        for key, value in attributes.items():
            value(self,"")
        
        
        with open(postFilePath,"r", encoding="utf-8") as postFile:
            postFileContent = postFile.read()
        
        #The first empty line splits content from header
        postHeader,postContent = postFileContent.split('\n\n',maxsplit=1)
        
        #Parse headers
        #TODO catch exceptions (valueError for dates...)
        headers = postHeader.splitlines()
        for header in headers:
            key,value = header.split(':',maxsplit=1)
            key=key.strip().lower()
            if key in attributes:
                attributes[key](self,val=value)
        
        attributes['file'](self,postFilePath)
        
        if self.position == "":
            self.position = "0";
        
        #if URL isn't set by writer, slugify the post title to use it as a URL
        #TODO check URL unicity
        if self.url == "":
            _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')
            result = []
            for word in _punct_re.split(self.title.lower()):
                result.append(unidecode.unidecode(word))
            self.url = "-".join(result)
        
        #if no tags are set ensure there wont be an empty tag created
        if "" in self.tags:
            self.tags.remove("")
        
        #Interpret post content markdown
        self.content = markdown.markdown(postContent)
        
        #Remove markdown and HTML from content for excerpt, keep only 40 first words
        cleanr = re.compile('<.*?>')
        self.excerpt = re.sub(cleanr, '',markdown.markdown(' '.join(postContent.split()[:40]) + "..."))

####################################################
# Retreive posts
####################################################

def getIndex(start=0,number=10):
    #Returns the posts for the index, showing $number public posts starting at $start
    with open("contentData.json", "r") as jsonFile:
        data = json.load(jsonFile);
    
    #Get offset to hide not yet published posts
    offset=0
    while(parseDate(data['posts'][offset]['date']) > datetime.now() and offset<len(data['posts'])):
        offset+=1
    start += offset

    #If trying to start after the last post
    if start>=len(data['posts']):
        return ([],False,True)
    
    #Retrieve posts
    indexData = []
    for post in data['posts'][start:start+number]:
        indexData.append(Post(post['file']))
    
    #Returns the posts, and wether the first returned is the latest post, and wether the last returned is the earliest post
    return (indexData,start == offset,indexData[-1].file == data['posts'][-1]['file'])

def getPostIdByUrl(url,draft=False):
    #Returns a post position in contentData JSON post/draft array, raises ValueError if not found
    with open("contentData.json", "r") as jsonFile:
        data = json.load(jsonFile);
    
    if draft:
        postList='drafts'
    else:
        postList='posts'
    
    for id,post in enumerate(data[postList]):
        if post['url'] == url:
            return id;
    raise ValueError

def getPostByUrl(url):
    #Returns a post from its URL, raises ValueError if not found
    with open("contentData.json", "r") as jsonFile:
        data = json.load(jsonFile);
    for id,post in enumerate(data['posts']):
        if post['url'] == url:
            return Post(post['file']);
    for id,post in enumerate(data['drafts']):
        if post['url'] == url:
            return Post(post['file']);
    raise ValueError

def getPostsByTag(tag):
    #Returns all posts having given tag (return can be empty)
    with open("contentData.json", "r") as jsonFile:
        data = json.load(jsonFile);
    posts = []
    if tag not in data['tags']:
        return []
    for url in data['tags'][tag]:
        posts.append(getPostByUrl(url))
    return posts

def getPostById(postId,draft=False):
    #Returns post given its position in the contentData json array
    if postId < 0:
        return None

    with open("contentData.json", "r") as jsonFile:
        data = json.load(jsonFile);

    if draft:
        postList="drafts"
    else:
        postList="posts"
    if postId >= len(data[postList]):
        return None
    return Post(data[postList][postId]['file']);

####################################################
# Pages
####################################################

@app.route('/refresh/<key>')
def refresh(key=None):
    #Refresh page allows the owner to refresh the contentData json. It requires the key set in refresh.key first line
    
    #Check key
    with open('refresh.key','r') as keyFile:
        goodKey = keyFile.read().splitlines()[0]
    if key==None or key!=goodKey:
        abort(404)

    #Check all files in posts
    files = [join('posts',f) for f in listdir('posts') if isfile(join('posts', f))]
    posts=[]
    for postFile in files:
        #TODO Error management
        posts.append(Post(postFile))

    #Sort them by date (Ealier to older) and then position (ascending)
    posts.sort(key=lambda p: p.position)
    posts.sort(key=lambda p: p.date,reverse=True)

    tags={}
    shortPublicPosts=[]
    shortDraftPosts=[]
    for post in posts:
        #Store published/planned posts and drafts in different arrays for easier parsing in index
        if post.status == 'public':
            #Tags are parsed only for public posts
            for tag in post.tags:
                if tag in tags:
                    tags[tag].append(post.url)
                else:
                    tags[tag] = [post.url]
            
            #Don't store post content or excerpt in the contentData json, only header info
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

    #Store JSON in contentData file
    with open("contentData.json", "w") as jsonFile:
        json.dump({"posts":shortPublicPosts,"drafts":shortDraftPosts,"tags":tags}, jsonFile, default=str)

    #Return JSON info for owner to give status
    js = json.dumps({"success":True,"posts":{"total":len(posts),"public":len(shortPublicPosts),"drafts":len(shortDraftPosts)},"tags":len(tags)})
    resp = Response(js, status=200, mimetype='application/json')
    return resp

@app.route('/')
@app.route('/page/<page>')
def index(page=1):
    postsPerPage=10
    page=int(page)
    #TODO Error handling
    posts,isFirst,isLast = getIndex((page-1)*postsPerPage,postsPerPage)
    return render_template('index.html',posts=posts,page=page,isFirst=isFirst,isLast=isLast)

@app.route('/post/<url>')
def post(url):
    #TODO Error Handling
    postId = getPostIdByUrl(url)
    if postId == -1:
        abort(404)
    #TODO Error Handling
    post = getPostById(postId)
    oldPost = getPostById(postId+1)
    newPost = getPostById(postId-1)
    return render_template('post.html', post=post, oldPost=oldPost, newPost=newPost)

@app.route('/draft/<url>')
def draft(url):
    #TODO Error Handling
    postId = getPostIdByUrl(url,draft=True)
    if postId == -1:
        abort(404)
    #TODO Error Handling
    post = getPostById(postId,draft=True)
    return render_template('post.html', post=post)

@app.route('/tag/<tag>')
def tag(tag):
    #TODO Error Handling
    posts=getPostsByTag(tag)
    return render_template('tags.html', posts=posts, tag=tag)

@app.route('/img/<img>')
def img(img):
    #TODO Error Handling
    return send_from_directory("posts/img",img);

