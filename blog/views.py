import os
import re
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Q
from django.forms import model_to_dict
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.views.decorators.http import require_GET
from markdown import Markdown

from blog.models import Blog
from endportal import utils
from logs.models import Log

markdown = Markdown(
    extensions=['markdown.extensions.extra', 'markdown.extensions.toc', 'markdown.extensions.codehilite', 'arithmatex'],
    extension_configs={
        # Enable line numbers.
        'markdown.extensions.codehilite': {'linenums': True},
        # Enable generic mode for katex, disable smart dollar because it breaks inline math.
        'arithmatex': {'generic': True, 'smart_dollar': False}
    },
    # They said that this can help to improve Chinese character issues.
    slugify=slugify)


def get_universal_context(path, sub_dir):
    """
    Fetches context components which are available in all kinds of blog pages. Including major categories, tags, recent
    articles, subdirectories and split access path.
    :param path: Access path string.
    :param sub_dir: Whether to process subdirectories or not.
    :return Default context dictionary.
    :rtype dict
    """
    # We use sets to prevent duplication.
    categories, tags, subdirectories = set(), set(), set()
    # We collect major categories and tags first.
    # A major category is the first part of access path string after splitting it by slashes.
    for blog in Blog.objects.all().only('publish_path', 'content_tags'):
        categories.add(blog.publish_path.split('/')[0])
        for tag in blog.content_tags.split(','):
            tags.add(tag)
    # We then collect recent articles.
    # We do not need all the information of those articles, just access path, publish date and title is enough.
    # TODO make the number of recent articles configurable.
    recent = Blog.objects.all().order_by('-publish_date').only('publish_path', 'publish_date', 'content_name')
    recent = recent[:min(5, len(recent))]
    recent = [(blog.content_name, blog.publish_date, blog.publish_path) for blog in recent]
    # We then get subdirectories if the current path is not root, since the subdirectories of root path is identical to
    # major categories.
    if sub_dir and path != '':
        for blog in Blog.objects.filter(publish_path__startswith=path):
            # Ignore the current path.
            if blog.publish_path == path:
                continue
            sub_path = blog.publish_path[len(path) + 1:].split('/')[0]
            # Ignore articles. We only want directories.
            if path + '/' + sub_path != blog.publish_path:
                subdirectories.add(sub_path)
    # The front-end template can not recognize empty sets, so we change them into nones.
    subdirectories = subdirectories or None
    # Parse requested access path. If the path is empty, leave it as an empty string instead.
    if path != '':
        href, path = '', path.split('/')
        for i in range(len(path)):
            href, path[i] = href + path[i] + '/', (href + path[i] + '/', path[i])
    return {'cate': categories, 'tags': tags, 'rect': recent, 'subd': subdirectories, 'path': path}


def blog_to_dict(blog, process_content=True):
    """
    Transforms a blog object into a dictionary. Special fields such as urls and tags are processed into lists.
    :param blog: Blog object.
    :param process_content: Whether to process the content field into HTML.
    :return: Dictionary form of the given blog.
    :rtype dict
    """
    blog = model_to_dict(blog)
    # Distinguish empty urls.
    if blog['content_urls'] != '':
        blog['content_urls'] = [tuple(url.strip().split(':::')) for url in blog['content_urls'].split('\n')]
    else:
        blog['content_urls'] = None
    blog['content_tags'] = blog['content_tags'].split(',')
    if not process_content:
        return blog
    # Now, we should handle content text.
    # Enumerate every content type that is supported, trigger a 404 error if none of them matches.
    if blog['content_type'] == 'markdown':
        blog['content_text'] = markdown.convert(blog['content_text'])
        # For markdowns, the only thing to do is to generate a menu list.
        # In order to do this, we collect all <h2> and <h3> fragments and their ids. The <h2> will be the outer layer,
        # while <h3> will be the inner layer. Too much layers will cause visual inconvenience so we have at most two.
        # We do not use the official markdown TOC plugin since it can not customize the number of layers we wanted.
        blog['content_menu'] = []
        for header in re.finditer(r'<h([23])\s+id="([^"]+)">(.+)</h', blog['content_text']):
            # Group one is the header type (i.e. <h2> or <h3>), group two and three are the id and title, respectively.
            pair = (header.group(3), header.group(2))
            if header.group(1) == '2':
                blog['content_menu'].append(pair)
            else:
                if len(blog['content_menu']) != 0 and blog['content_menu'][-1][0] is None:
                    # If the last item in the menu is already a list, all we have to do is to append the current <h3> to
                    # it.
                    blog['content_menu'][-1][1].append(pair)
                else:
                    blog['content_menu'].append((None, [pair]))
        return blog

    # Unrecognizable content type.
    raise Http404()


@require_GET
def content(request, path):
    """
    Blog content page: accepts an access path, and returns the corresponding page.
    If the path has a matching blog, render that blog.
    If the path has not matching blog, but it is the prefix of one or more blogs (i.e. there exists blogs under this
    directory), render an index page.
    Otherwise, trigger a 404 error.
    """
    path = unquote('/'.join(path[:-1].split('/')))  # remove the trailing slash
    # Add log even if the request failed.
    Log.new_log(request, 'blog', 'access', path)
    context = get_universal_context(path, True)
    # Assume that there is a matching blog.
    try:
        context.update(blog_to_dict(Blog.objects.get(publish_path=path)))
        return render(request, 'blog-content.html', context)
    except Blog.DoesNotExist:
        # If the blog specified by this path does not exists, then check if there are any blogs under this directory. If
        # yes, display an index page. Otherwise, return 404.
        query_set = Blog.objects.filter(publish_path__startswith=path).order_by('-publish_date')
        # Note that empty path (i.e. root) will never raise 404, otherwise there will be no entrance if there are no
        # blogs online.
        if len(query_set) == 0 and path != '':
            raise Http404()
        context['page'], context['plim'], context['pcnt'], context['blog'] = utils.paginate(request, 10, query_set)
        context['blog'] = [blog_to_dict(blog, False) for blog in context['blog']]
        return render(request, 'blog-indices.html', context)


@require_GET
def indices(request):
    """
    Search page: accepts a keyword and search for it in titles and tags. Renders the search result as an index page.
    """
    keyword = unquote(request.GET.get('keyword', ''))
    # Add log in all cases.
    Log.new_log(request, 'blog', 'search', keyword)
    # We should disable subdirectories since this is not a real access path.
    context = get_universal_context('', False)
    query_set = Blog.objects \
        .filter(Q(content_name__icontains=keyword) | Q(content_tags__icontains=keyword)) \
        .order_by('-publish_date')
    context['page'], context['plim'], context['pcnt'], context['blog'] = utils.paginate(request, 10, query_set)
    context['blog'] = [blog_to_dict(blog, False) for blog in context['blog']]
    # This parameter is used to fill out the default value of the search bar.
    context['skey'] = keyword
    return render(request, 'blog-indices.html', context)


@login_required()
@user_passes_test(lambda u: u.is_superuser)
def publish(request):
    """
    Publish page: Simply renders the publish form if the request method is GET, or actually publishes (creates or
    modifies) a blog if the request method if POST.
    """
    # Check the request method to distinguish between page requests and actual publishes.
    if request.method == 'GET':
        context = get_universal_context('', False)
        # Add field 'stit' so that the edit option will not appear in the top-right menu again.
        context['stit'] = ''
        # Get an existing blog from database and fill out the default values, if an `id` is given. Otherwise, this is
        # creation, nothing to be done.
        if 'id' in request.GET:
            try:
                context.update(model_to_dict(Blog.objects.get(id=int(request.GET.get('id')))))
            except Blog.DoesNotExist or ValueError:
                raise Http404()
        return render(request, 'blog-publish.html', context)

    if request.method == 'POST':
        if 'id' in request.POST:
            try:
                blog = Blog.objects.get(id=int(request.POST.get('id')))
            except Blog.DoesNotExist or ValueError:
                raise Http404()
        else:
            # This is required because django refuses to create a new blog object with empty publish date.
            blog = Blog.objects.create(publish_date=request.POST.get('publish_date'))
        # Handle static resources first.
        # Validate the uploaded files first, if any of them is invalid, the whole publish request will not be handled.
        for image in request.FILES.getlist('static_files'):
            if image.size > 10485760:  # 10M
                return JsonResponse({'error': image.name + '体积过大'})
        for image in request.FILES.getlist('static_files'):
            # Although we do not restrict the type of uploaded files, we still store all those files under `image`
            # directory.
            # TODO this may be improvable.
            with open(os.path.join(settings.STATIC_ROOT, 'images', image.name), 'wb') as f:
                for chunk in image.chunks():
                    f.write(chunk)
        # Iterate through all fields and update them. It is guaranteed that the POST parameters' name is the same as
        # database columns.
        for field in Blog._meta.fields:
            if field.name != 'id':
                blog.__setattr__(field.name, request.POST.get(field.name, ''))
        blog.save()
        # Since publishing blogs require certain privileges, we only log if a publish succeeded.
        Log.new_log(request, 'blog', 'publish', str(blog.id))
        return redirect('blog-content', path=blog.publish_path + '/')  # the trailing slash is vital
