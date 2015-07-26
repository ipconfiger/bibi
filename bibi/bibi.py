#!/usr/bin/python
#coding=utf8
__author__ = 'liming'

import os
import sys
import datetime
import logging
import shutil
import markdown
import yaml
from flask import Flask, jsonify
from flask.ext.script import Manager
from jinja2.loaders import DictLoader, FunctionLoader
from jinja2 import Environment, nodes
from jinja2.ext import Extension
from pygments import highlight
from pygments.lexers import get_lexer_by_name, PythonLexer
from pygments.formatters import HtmlFormatter
from pygments.filters import VisibleWhitespaceFilter


SITE_FOLDER = '_site'
POSTS_FOLDER = '_post'
LAYOUTS_FOLDER = '_layouts'
INCLUDE_FOLDER = '_include'
CSS_FOLDER = '_css'
MARKDOWN_FILES = ['md', 'markdown']
HTML_FILES = ['html', 'htm']
CONFIG = '_config.yaml'

app = Flask(__name__, static_url_path='')
manager = Manager(app)

proj = os.path.split(os.getcwd())[-1]


class FragmentGistExtension(Extension):
    """
    支持贴入gist代码
    """
    tags = set(['gist'])

    def __init__(self, environment):
        super(FragmentGistExtension, self).__init__(environment)

    def parse(self, parser):
        parser.stream.next()
        args = [parser.parse_expression()]
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        gist_id = "%s/%s" % (args[0].left.name, args[0].right.value)
        node = nodes.TemplateData()
        node.data = '<script src="https://gist.github.com/%s.js"></script>' % gist_id
        return node


class FragmentHighlightExtension(Extension):
    """
    代码高亮
    """
    tags = set(['highlight'])

    def __init__(self, environment):
        super(FragmentHighlightExtension, self).__init__(environment)


    def parse(self, parser):
        parser.stream.next()

        args = [parser.parse_expression()]

        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))
        lng_name = args[0].name

        body = parser.parse_statements(['name:endhighlight'], drop_needle=True)
        origin_str = body[0].nodes[0].data
        lexer = get_lexer_by_name(lng_name)
        lexer.filters.append(VisibleWhitespaceFilter())
        result = highlight(origin_str, lexer, HtmlFormatter())
        body[0].nodes[0].data = result

        return body


def date_to_string(date):
    """
    格式化日期的过滤器
    :param date: 日期
    :return:日期字符串
    """
    return u"%s年%s月%s日" % (date.year, date.month, date.day)


def limit(iterer, n):
    """
    限制输出序列数量的过滤器
    :param iterer: 序列
    :param n: 限制数量
    :return:裁剪后序列
    """
    return iterer[:n]


def disqus(short_name):
    return """<div id="disqus_thread"></div>
    <script type="text/javascript">
        /* * * CONFIGURATION VARIABLES: EDIT BEFORE PASTING INTO YOUR WEBPAGE * * */
        var disqus_shortname = '%s'; // required: replace example with your forum shortname

        /* * * DON'T EDIT BELOW THIS LINE * * */
        (function() {
            var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
            dsq.src = '//' + disqus_shortname + '.disqus.com/embed.js';
            (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
        })();
    </script>
    <noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript">comments powered by Disqus.</a></noscript>
    <a href="http://disqus.com" class="dsq-brlink">comments powered by <span class="logo-disqus">Disqus</span></a>
""" % short_name


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


class Page(object):
    """
    page对象
    """
    url = None
    key = None
    layout = None
    directory = None
    title = None
    date = None
    template_str = None
    template_instance = None


class Post(object):
    """
    post对象
    """
    url = None
    title = None
    content = None
    date = None
    author = None
    tags = None

class Paginator(object):
    """
    分页器对象
    """
    posts = []
    page = None
    per_page = None
    total_posts = None
    total_pages = None
    previous_page = None
    previous_page_path = None
    next_page = None
    next_page_path = None

class Site(object):
    """
    站点对象
    """
    pages = []
    posts = []
    tags = []
    config = {}

class Generator(object):
    """
    页面生成器
    """
    def __init__(self):
        self.site = Site()
        self.site.pages = []
        self.site.posts = []
        self.site.tags = ()
        self.templates = {}
        self.context_propertys = {}
        self.context_instances = {}
        self.template_name_map = {}
        self.includes = []
        self._get_files(LAYOUTS_FOLDER, allow_ext=['.html', '.htm'])
        self._get_files(INCLUDE_FOLDER, allow_ext=['.html', '.htm'])
        self._get_files("", allow_ext=['.html', '.htm', '.xml', '.md', '.markdown'])
        self._get_files(POSTS_FOLDER, allow_ext=['.md', '.markdown'])
        self.paginator = None

        config_path = os.path.join(os.getcwd(), CONFIG)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.load(f.read())
                for k, v in config.iteritems():
                    if k == 'paginate':
                        self.paginator = Paginator()

                    setattr(self.site, k, v)
        self.config_env()


    def load_template(self, name):
        """
        加载模板的函数
        :param name:模板文件名
        :return:
        """
        if name in self.templates:
            return self.templates.get(name)
        return ""

    def config_env(self):
        """
        设置模板环境
        :return:
        """
        self.env = Environment(
            loader=FunctionLoader(self.load_template),
            extensions=[
                FragmentHighlightExtension,
                FragmentGistExtension,
            ],
            auto_reload=True,
            cache_size=0
        )
        self.env.filters['date_to_string'] = date_to_string
        self.env.filters['limit'] = limit
        self.env.filters['disqus'] = disqus


    def _process_header(self, file):
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


    def _parse_filename(self, file_name):
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


    def _get_files(self, folder='_post', allow_ext=None):
        """
        获取文件
        :param folder:目录名
        :param markdown:是否是markdown文件
        :return: [[file name, file data]]
        """
        path = os.path.join(os.getcwd(), folder)
        if not os.path.exists(path):
            print "Not in project directory"
        file_paths = os.listdir(path)
        for file_name in file_paths:
            if os.path.splitext(file_name)[1] not in allow_ext:
                continue
            file_path = os.path.join(path, file_name)
            if os.path.exists(file_path):
                dt = datetime.datetime.fromtimestamp(os.stat(file_path).st_mtime)
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    propertys, template_html = self._process_header(file_content)
                    propertys.update(dict(date=dt))
                    if folder==POSTS_FOLDER:
                        propertys.update(dict(is_content=True))
                    else:
                        propertys.update(dict(is_content=False))
                    if folder=='':
                        propertys.update(dict(is_page=True))
                    else:
                        propertys.update(dict(is_page=False))
                    self.templates[file_name] = template_html.decode('utf-8')
                    self.template_name_map[os.path.splitext(file_name)[0]] = file_name
                    self.context_propertys[file_name] = propertys

                    if folder == INCLUDE_FOLDER:
                        self.includes.append(file_name)


    def _render(self, layout, context):
        """
        递归渲染模板
        """
        if layout and layout in self.template_name_map:
            template = self.env.get_template(self.template_name_map.get(layout))
            html = template.render(**context)
            context['content'] = html
            file_name = self.template_name_map.get(layout)
            ppt = self.context_propertys.get(file_name)
            if ppt:
                return self._render(ppt.get('layout'), context)
            return html
        return context['content']


    def _render_page(self, context):
        """
        渲染页面
        """
        if context['content']:
            layout = context['page'].layout
        else:
            layout = os.path.splitext(context['page'].file_name)[0]

        if self.paginator and context['page'].file_name in ['index.html', 'index.htm']:
            page_size = self.site.paginate
            self.paginator.total_posts = len(self.site.posts)
            self.paginator.total_pages = self.paginator.total_posts / page_size
            for pid in range(self.paginator.total_pages):
                file_name = context['page'].file_name
                ext = os.path.splitext(file_name)[1]
                self.paginator.page = pid+1
                self.paginator.posts = self.site.posts[pid*page_size: (pid+1)*page_size]
                self.paginator.previous_page = pid if pid else None
                self.paginator.next_page = pid+1
                if pid>0:
                    self.paginator.previous_page_path = "/%s" % file_name
                    if pid<self.paginator.total_pages:
                        self.paginator.next_page_path = "/%s_%s%s" % (layout, self.paginator.page+1, ext)
                else:
                    if pid<self.paginator.total_pages:
                        self.paginator.next_page_path = "/%s_%s%s" % (layout, self.paginator.page+1, ext)
                html = self._render(layout, context)
                self.dump_file(html, context)
        else:
            html = self._render(layout, context)
            self.dump_file(html, context)



    def dump_file(self, html, context):
        """
        输出到文件
        """
        base_path = os.path.join(os.getcwd(), SITE_FOLDER)
        if context['post']:
            dir_path = os.path.join(base_path, context['page'].directory)
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
            file_path = os.path.join(dir_path, context['page'].file_name)
        else:
            if self.paginator and context['page'].file_name in ['index.html', 'index.htm']:
                if self.paginator.page>1:
                    file_name = context['page'].file_name
                    file_path = os.path.join(base_path,"%s_%s%s" % (
                        os.path.splitext(file_name)[0],
                        self.paginator.page,
                        os.path.splitext(file_name)[1]
                    ))
                else:
                    file_path = os.path.join(base_path, context['page'].file_name)
            else:
                file_path = os.path.join(base_path, context['page'].file_name)
        with open(file_path, 'w+') as f:
            f.write(html.encode('utf8'))
        print context['page'].file_name, "process ok!"


    def copytree(self, src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

    def move_ext_dictionary(self):
        paths = os.listdir(os.getcwd())
        tar_path = os.path.join(os.getcwd(), SITE_FOLDER)
        for filename in paths:
            path = os.path.join(os.getcwd(), filename)
            dir_name = os.path.split(path)[1]
            if not dir_name.startswith("_") and not dir_name.startswith(".") and not os.path.isfile(path):
                tar_dir = os.path.join(tar_path, dir_name)
                if not os.path.exists(tar_dir):
                    os.mkdir(tar_dir)
                print "copy", path, "to", tar_dir
                self.copytree(path, tar_dir)


    def parse_file(self):
        self.move_ext_dictionary()
        contexts = []
        for file_name, property in self.context_propertys.iteritems():
            if 'layout' not in property:
                continue
            if property.get('is_content') or property.get('is_page'):
                page = Page()
                page.url = u"/%s" % file_name.decode('utf-8')
                page.key = file_name
                page.directory = ''
                page.title = property.get('title', u'')
                page.date = property.get('date')
                page.file_name = file_name
                page.layout = property.get('layout')
                page.template_instance = self.env.get_template(file_name)
                page.template_str = self.templates.get(file_name)
                context = dict(page=page, content="", post=None, site=self.site, paginator=self.paginator)

                if property.get('is_content'):
                    dt, dt_str, save_name = self._parse_filename(file_name)
                    post = Post()
                    post.url = u"/%s/%s" % (dt_str.decode('utf-8'), save_name.decode('utf-8'))
                    post.date = dt
                    post.title = property.get('title')
                    post.author = property.get('author', 'anonymous')
                    post.content = markdown.markdown(page.template_instance.render(content=''))
                    post.tags = set(property.get('tags', '').split(','))
                    self.site.tags = set(list(self.site.tags) + list(post.tags))
                    page.file_name = save_name
                    page.directory = dt_str
                    post.date = dt
                    context['post'] = post
                    context['content'] = post.content
                    self.site.posts.append(post)
                if property.get('is_page'):
                    if not os.path.splitext(file_name)[0] == 'index':
                        self.site.pages.append(page)
                contexts.append(context)

        self.site.posts.sort(key=lambda item:item.date, reverse=True)

        for context in contexts:
            self._render_page(context)


@manager.command
def gen():
    """
    生成内容
    :return:
    """
    generator = Generator()
    generator.parse_file()

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
    conf = """
server {
 listen          80;
 server_name     %s;
 location / {
  root  %s;
  index index.html;
 }
}
    """ % (domain, os.path.join(os.getcwd(), SITE_FOLDER))
    sys.stdout.write(conf)


@manager.command
def hook_conf(port, log_file):
    conf = """[program:%s]
command=/usr/bin/python bibi.py runserver --host 0.0.0.0 --port %s
directory=%s
umask=022
startsecs=0
stopwaitsecs=0
redirect_stderr=true
stdout_logfile=%s
autorestart=true
autostart=true
""" % (proj, port, os.getcwd(), log_file)
    sys.stdout.write(conf)

@manager.command
def new_post(title):
    template = """---
layout: post
title: %s
---


""" % title
    dt = datetime.datetime.now()
    file_name = "%s-%02d-%02d-%s.md" % (dt.year, dt.month, dt.day, title)
    dir_path = os.path.join(os.getcwd(), POSTS_FOLDER)
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'w') as f:
        f.write(template)
    print template
    os.system("open _post/%s" % file_name )



@app.route('/hook', methods=['POST', 'GET'])
def webhook():
    import git
    logging.error("get notification!")
    g = git.cmd.Git(os.getcwd())
    g.pull()
    logging.error("git pull ok!")
    gen()
    logging.error("finish generate!")
    return jsonify(status="ok")


def main():
    manager.run()


if __name__ == "__main__":
    main()
