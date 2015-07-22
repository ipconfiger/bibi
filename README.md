# bibi
Static blog generator

## Useage

1. Installation


    $sudo pip install bibi


2. Create Site


    $bibi project project_name


this command will create folder project_name and the structure of project.

    ---priject_name
     |----_layouts
     |----_posts
     |----_site
 
 put markdown files in _post folder
 
 put template files in _layouts folder
 
 html files generated will store in _site folder
 
3. Generate html files


    $cd project_name
    $bibi gen


4. Preview Site


    $bibi test 8000


5. Generate nginx conf file
  so you can host blog on your own server


    $bibi nginx_conf domain_name


6. Generate supervisor conf file
  host web hook service on supervior, the blog site will update automatically when you push to github


    $bibi hook_conf /var/log/hook.log


