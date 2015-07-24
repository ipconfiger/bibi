# bibi
Static blog generator

-------------------
本来今天下午打算增加个scss生成的功能好自动从jekyll的模板里自动生成css，但是试用过一堆python的scss库后，我被自己蠢哭了，这堆玩意儿不是为我这种等级的智商的人准备的，所以可能需要自己写一个scss解析的库

分页支持已经提供了，文档回头写，基本上和jekyll差不多

## Useage

### Installation

    $sudo pip install bibi

### Create Site

    $bibi project project_name


this command will create folder project_name and the structure of project.

    ---priject_name
     |----_layouts
     |----_posts
     |----_site
 
 put markdown files in _post folder
 
 put template files in _layouts folder
 
 html files generated will store in _site folder
 
### Generate html files

command must run in project folder

    $cd project_name
    $bibi gen


### Preview Site

you can preview site after you generate html files

    $bibi test 8000


### Generate nginx conf file

so you can host blog on your own server


    $bibi nginx_conf domain_name


### Generate supervisor conf file

host web hook service on supervior, the blog site will update automatically when you push to github


    $bibi hook_conf /var/log/hook.log
    
### Code hightlighting

    {% highlight python %}
        def func():
            print "hello world"
    {% endhighlight %}

you need stylesheet of pygments

Tips: becarefull of you css reset, it may cause python code miss ident

### Paste code from gist

    {% gist account/gist_id %}
    
for example {% gist ipconfiger/6142002 %}

### Limit String length or list length

    {{ post.title | limit(20) }}

will show 20 character
OR

    {% for post in site.posts | limit(5) %}
    
will show 5 posts

### Create new post

    $bibi new_post post_name
    
if you use mac,this command will try to open markdown editor to edit new file
