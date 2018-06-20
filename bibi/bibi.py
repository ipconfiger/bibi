#!/usr/bin/python
#coding=utf8
__author__ = 'liming'

import os
import sys
import datetime
import shutil
import markdown
import yaml
import click

from six import iteritems
from jinja2.loaders import FunctionLoader
from jinja2 import Environment, nodes
from jinja2.ext import Extension



SITE_FOLDER = '_site'
POSTS_FOLDER = '_post'
LAYOUTS_FOLDER = '_layouts'
INCLUDE_FOLDER = '_include'
ASSETS_FOLDER = '_assets'
MARKDOWN_FILES = ['md', 'markdown']
HTML_FILES = ['html', 'htm']
CONFIG = '_config.yaml'



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


def sorts(iterer, property, direction):
    """
    根据meta属性排序
    :param iterer:
    :type iterer:
    :param property:
    :type property:
    :param direction:
    :type direction:
    :return:
    :rtype:
    """
    if direction == 'desc':
        return sorted(iterer, key=lambda item: item.meta[property], reverse=True)
    return sorted(iterer, key=lambda item: item.meta[property])


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
    page_size = None
    page_filter = None
    page_sort = None


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
    meta = None

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
    paginate = 10

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
        self.paginator = Paginator()

        config_path = os.path.join(os.getcwd(), CONFIG)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.load(f.read())
                for k, v in iteritems(config):
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
                FragmentGistExtension,
            ],
            auto_reload=True,
            cache_size=0
        )
        self.env.filters['date_to_string'] = date_to_string
        self.env.filters['limit'] = limit
        self.env.filters['disqus'] = disqus
        self.env.filters['sort'] = sorts


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
                spliter_idx = line.index(':')
                key = line[:spliter_idx].strip()
                value = line[spliter_idx + 1:].strip()
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
            click.echo("Not in project directory")
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

        if self.paginator and context['page'].page_size > 0:
            click.echo('paging......')
            page_size = context['page'].page_size
            all_items = self.site.posts
            if context['page'].page_sort:
                key, direction = context['page'].page_sort.split('=')
                if direction.lower() == 'desc':
                    all_items = sorted(all_items, key=lambda item: item.meta[key], reverse=True)
                else:
                    all_items = sorted(all_items, key=lambda item: item.meta [key])
            if context['page'].page_filter:
                query_dt = dict([sq.split('=') for sq in context ['page'].page_filter.split('&')])
                for key, value in iteritems(query_dt):
                    all_items = [item for item in all_items if item.meta.get(key.strip(), '')==value.strip()]

            self.paginator.total_posts = len(all_items)
            self.paginator.total_pages = self.paginator.total_posts / page_size
            for pid in range(self.paginator.total_pages):
                file_name = context['page'].file_name
                ext = os.path.splitext(file_name)[1]
                self.paginator.page = pid+1
                self.paginator.posts = all_items[pid*page_size: (pid+1)*page_size]
                self.paginator.previous_page = pid if pid else None
                self.paginator.next_page = pid+1 if pid + 1 < page_size else None
                if pid>0:
                    self.paginator.previous_page_path = "/%s" % file_name
                    if pid<self.paginator.total_pages:
                        self.paginator.next_page_path = "/%s_%s%s" % (layout, self.paginator.page+1, ext)
                else:
                    if pid<self.paginator.total_pages:
                        self.paginator.next_page_path = "/%s_%s%s" % (layout, self.paginator.page+1, ext)
                context['paginator'] = self.paginator
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
            if self.paginator and context['page'].page_size > 0:
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
        click.echo(context['page'].file_name + " process ok!")


    def move_ext_dictionary(self):
        tar_path = os.path.join(os.getcwd(), SITE_FOLDER)
        shutil.rmtree(tar_path)
        os.mkdir(tar_path)
        asset_path = os.path.join(os.getcwd(), ASSETS_FOLDER)
        paths = os.listdir(asset_path)
        
        for filename in paths:
            src_path = os.path.join(asset_path, filename)
            if os.path.isfile(src_path):
                shutil.copy(src_path, os.path.join(tar_path, filename))
            else:
                shutil.copytree(src_path, os.path.join(tar_path, filename))
            click.echo('copy %s to %s done' % (src_path, tar_path))


    def parse_file(self):
        self.move_ext_dictionary()
        contexts = []
        for file_name, property in iteritems(self.context_propertys):
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
                page.meta = property
                page.page_size = int(property.get('page_size', '0'))
                page.page_filter = property.get('page_filter', '')
                page.page_sort = property.get('page_sort', '')
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
                    post.meta = property
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


@click.group()
def cli():
    pass


@click.command()
@click.argument('project_name')
def project(project_name):
    """
    创建一个project
    :param name: 站点的名字
    :return:
    """
    path = os.path.join(os.getcwd(), project_name)
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        click.echo('project exists')
        return sys.exit(1)
    post_path = os.path.join(path, POSTS_FOLDER)
    os.mkdir(post_path)
    layout_path = os.path.join(path, LAYOUTS_FOLDER)
    os.mkdir(layout_path)
    site_path = os.path.join(path, SITE_FOLDER)
    os.mkdir(site_path)
    include_path = os.path.join(path, INCLUDE_FOLDER)
    os.mkdir(include_path)
    assets_path = os.path.join(path, ASSETS_FOLDER)
    os.mkdir(assets_path)

    with open(os.path.join(path, CONFIG), 'w') as f:
        f.write((u'site_name: %s\n' % project_name).encode('utf8'))
        f.write((u'paginate: 10\n').encode('utf8'))

    click.echo("project %s inited" % project_name)


@click.command()
@click.argument('title')
def new_post(title):
    template = """---
layout: post
title: %s
author: me
---
""" % title
    dt = datetime.datetime.now()
    file_name = "%s-%02d-%02d-%s.md" % (dt.year, dt.month, dt.day, title)
    dir_path = os.path.join(os.getcwd(), POSTS_FOLDER)
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'w') as f:
        f.write(template)
    click.echo(template)
    os.system("open _post/%s" % file_name )


@click.command()
def gen():
    """
    生成内容
    :return:
    """
    generator = Generator()
    generator.parse_file()

    click.echo("all process done")


@click.command()
@click.argument('port')
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
    click.echo("Serving HTTP on %s port %s ..." % (sa[0], sa[1]))
    httpd.serve_forever()


def main():
    cli.add_command(project)
    cli.add_command(gen)
    cli.add_command(test)
    cli.add_command(new_post)
    cli()


if __name__ == "__main__":
    main()
