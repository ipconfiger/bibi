#!/usr/bin/python
#coding=utf8
__author__ = 'liming'

import os
import sys
import datetime
import markdown
from flask import Flask, jsonify
from flask.ext.script import Manager
from jinja2.loaders import DictLoader
from jinja2 import Environment

SITE_FOLDER = '_site'
POSTS_FOLDER = '_post'
LAYOUTS_FOLDER = '_layouts'
INCLUDE_FOLDER = '_include'
MARKDOWN_FILES = ['md', 'markdown']
HTML_FILES = ['html', 'htm']

app = Flask(__name__, static_url_path='')
manager = Manager(app)

proj = os.path.split(os.getcwd())[-1]


def date_to_string(date):
    return u"%s年%sd月%s日" % (date.year, date.month, date.day)


def get_files(folder='_post', markdown=True):
    """
    获取文件
    :param folder:目录名
    :param markdown:是否是markdown文件
    :return: [[file name, file data]]
    """
    files = []
    path = os.path.join(os.getcwd(), folder)
    if not os.path.exists(path):
        print "Not in project directory"
    file_paths = os.listdir(path)
    for file_name in file_paths:
        if markdown:
            if file_name.split('.')[-1] not in MARKDOWN_FILES:
                continue
        else:
            if file_name.split('.')[-1] not in HTML_FILES:
                continue
        file_path = os.path.join(path, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                files.append([file_name, f.read()])
    return files


def process_header(file):
    """
    处理文件头部meta数据
    :param file:文件内容
    :return: meta字典, 后面的内容
    """
    lines = file.split('\n')
    if not lines[0].startswith('---'):
        return {}, file
    idx = 0
    propertys = {}
    for line in lines[1:]:
        if line.startswith('---'):
            idx+=1
            break
        else:
            key, value = line.split(':')[:2]
            propertys[key.strip()] = value.strip().decode('utf-8')
            idx+=1
    return propertys, "\n".join(lines[idx+1:])


def parse_filename(file_name):
    """
    从文件名提取日期和后缀
    :param file_name: 文件名
    :return:日期对象，日期字符串（用作目录名）, 文件名
    """
    slice = file_name.split('-')
    date = datetime.datetime(*map(int, slice[:3]))
    title_name = os.path.splitext("-".join(slice[3:]))[0]
    date_str = "-".join(slice[:3])
    return date, date_str, "%s.html" % title_name


def render_template(template, context):
    """
    渲染页面
    :param template: 模板对象
    :param context: 环境变量
    :return:
    """
    template.render(**context)


def process_data(datas):
    """
    处理POST数据
    :param datas: 待处理的数据列表
    :return: 处理完成的数据列表
    """
    results = []
    for file_name, data_str in datas:
        propertys, content_str = process_header(data_str)
        dt, dt_str, save_name = parse_filename(file_name)
        propertys.update(
            dict(
                date=dt,
                file_name=save_name.decode('utf-8'),
                dir=dt_str.decode('utf-8'),
                content=markdown.markdown(content_str.decode('utf-8')),
                url=u"/%s/%s" % (dt_str.decode('utf-8'), save_name.decode('utf-8'))
            )
        )
        results.append(propertys)
    return results

def process_page(datas):
    results = []
    for file_name, data_str in datas:
        propertys, content_str = process_header(data_str)
        propertys.update(
            dict(
                file_name=file_name,
                content=content_str.decode('utf-8'),
                url=u"/%s" % file_name.decode('utf-8')
            )
        )
        results.append(propertys)
    return results


def render_pages(layout, template_dict, **propertys):
    template_item = template_dict.get(layout, None)
    if template_item:
        template_ppt = template_item.get('ppt')
        template = template_item.get('template')
        html_file = template.render(**propertys)
        if template_ppt.get('layout', None):
            propertys.update(dict(content=html_file))
            return render_pages(template_ppt.get('layout'), template_dict, **propertys)
        return html_file
    else:
        return propertys.get("content", '')


def render_post(post, site, template_dict):
    layout = post.get('layout', '')
    if layout not in template_dict:
        print "post %s not define a layout [%s]" % (post.get('title'), layout)
        return

    html_file = render_pages(layout, template_dict, content=post.get('content'), site=site, page=post, post=post)

    dir = post.get('dir')
    file_name = post.get('file_name')
    base_folder = os.path.join(os.getcwd(), SITE_FOLDER)
    dir_folder = os.path.join(base_folder, dir)
    if not os.path.exists(dir_folder):
        os.mkdir(dir_folder)
    file_path = os.path.join(dir_folder, file_name)
    with open(file_path, 'w+') as f:
        f.write(html_file.encode('utf-8'))
    print u"post:%s process done!" % post.get('title')


def render_single_page(page, site, template_dict):
    file_name = page.get('file_name')
    layout = os.path.splitext(file_name)[0]
    if layout not in template_dict:
        print "page %s not define a layout [%s]" % (page.get('file_name'), layout)
        return
    html_file = render_pages(layout, template_dict, content=page.get('content'), site=site, page=page, post=page)
    base_folder = os.path.join(os.getcwd(), SITE_FOLDER)
    file_path = os.path.join(base_folder, file_name)
    with open(file_path, 'w+') as f:
        f.write(html_file.encode('utf-8'))
    print u"page:%s process done!" % file_name

@manager.command
def project(name):
    """
    创建一个project
    :param name: 站点的名字
    :return:
    """
    path = os.path.join(os.getcwd(), name)
    if not os.path.exists(path):
        os.mkdir(path)
    post_path = os.path.join(path, POSTS_FOLDER)
    os.mkdir(post_path)
    layout_path = os.path.join(path, LAYOUTS_FOLDER)
    os.mkdir(layout_path)
    site_path = os.path.join(path, SITE_FOLDER)
    os.mkdir(site_path)
    include_path = os.path.join(path, INCLUDE_FOLDER)
    os.mkdir(include_path)

    print "project %s inited" % name


@manager.command
def gen():
    """
    生成内容
    :return:
    """
    templates = get_files(folder=LAYOUTS_FOLDER, markdown=False)
    pages = get_files(folder='', markdown=False)
    markdowns = get_files(folder=POSTS_FOLDER, markdown=True)

    template_env_dict = {}
    template_dict = {}
    for file_name, temp_file in templates:
        propertys, template_html = process_header(temp_file)
        template_dict[file_name] = dict(ppt=propertys, template=None)
        template_env_dict[file_name] = template_html.decode('utf-8')

    for file_name, page_html in pages:
        propertys, template_html = process_header(page_html)
        template_dict[file_name] = dict(ppt=propertys, template=None)
        template_env_dict[file_name] = template_html.decode('utf-8')

    env = Environment(loader=DictLoader(template_env_dict))
    env.filters['date_to_string'] = date_to_string

    process_template_dict = {}
    for file_name, meta in template_dict.iteritems():
        template = env.get_template(file_name)
        propertys = template_dict[file_name]
        propertys["template"] = template
        process_template_dict[os.path.splitext(file_name)[0]] = propertys

    site = {}
    site['pages'] = process_page(pages)
    posts = process_data(markdowns)
    sorted_posts = sorted(posts,key=lambda post:post.get('date'), reverse=True)
    site['posts'] = sorted_posts

    for post in posts:
        render_post(post, site, process_template_dict)

    for page in site.get('pages'):
        render_single_page(page, site, process_template_dict)

    print "all process done"


@manager.command
def test(port):
    import BaseHTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    os.chdir(os.path.join(os.getcwd(), SITE_FOLDER))
    HandlerClass = SimpleHTTPRequestHandler
    ServerClass  = BaseHTTPServer.HTTPServer
    Protocol = "HTTP/1.0"
    server_address = ('127.0.0.1', int(port))
    HandlerClass.protocol_version = Protocol
    httpd = ServerClass(server_address, HandlerClass)
    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


@manager.command
def nginx_conf(domain):
    return """
server {
 listen          80;
 server_name     %s;
 location / {
  root  %s;
  index index.html;
 }
}
    """ % (domain, os.path.join(os.getcwd(), SITE_FOLDER))


@manager.command
def hook_conf(port, log_file):
    return """[program:img]
command=/usr/bin/python bibi.py runserver --host 0.0.0.0 --port %s
directory=%s
umask=022
startsecs=0
stopwaitsecs=0
redirect_stderr=true
stdout_logfile=%s
autorestart=true
autostart=true
""" % (port, os.getcwd(), log_file)


@app.route('/hook', methods=['POST', 'GET'])
def webhook():
    import git
    g = git.cmd.Git(os.getcwd())
    g.pull()
    gen()
    return jsonify(status="ok")


def main():
    manager.run()


if __name__ == "__main__":
    main()
