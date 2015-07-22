# bibi
Static blog generator

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


