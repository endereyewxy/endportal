import os
import re
from datetime import datetime
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


def get_universal_context(path, sub_dir=True):
    """
    Get category list, tags, recent articles and subdirectories which are used in any circumstances. Will also split
    and process path string into a list consisting of link href and title, in order to generate information required
    by breadcrumb.
    :param path: The path string.
    :param sub_dir: If subdirectory enabled.
    :return A default context.
    :rtype dict
    """
    # Collect categories (the first directory of publish path) and tags.
    categories, tags = set(), set()
    for blog in Blog.objects.all().only('publish_path', 'content_tags'):
        categories.add(blog.publish_path.split('/')[0])
        for tag in blog.content_tags.split(','):
            tags.add(tag)
    # Collect 5 most recent articles.
    query_set = Blog.objects.all().order_by('-publish_date').only('publish_path', 'publish_date', 'content_name')
    query_set = query_set[:min(5, len(query_set))]
    recent = [(blog.content_name, blog.publish_date, blog.publish_path) for blog in query_set]
    # Get subdirectories if the current path is not root.
    subd = set()
    if sub_dir and path != '':
        for blog in Blog.objects.filter(publish_path__startswith=path):
            if blog.publish_path == path:
                continue
            sub_path = blog.publish_path[len(path) + 1:].split('/')[0]
            # Ignore articles
            if path + '/' + sub_path != blog.publish_path:
                subd.add(sub_path)
    # The front-end template can not recognize empty sets, so we change them into none values.
    if len(subd) == 0:
        subd = None
    # Parse requested path. If the path is empty, return an empty string instead.
    if len(path) > 0:
        href, path = '', path.split('/')
        for i in range(len(path)):
            href, path[i] = href + path[i] + '/', (href + path[i] + '/', path[i])
    return {'cate': categories, 'tags': tags, 'rect': recent, 'path': path, 'subd': subd}


def blog_to_dict(blog, process_content=True):
    """
    Get a dictionary containing data of a given blog object. Special fields such as urls and tags are processed into
    list.
    :param blog: Blog object.
    :param process_content: Whether to process the content field into HTML and add menu field.
    :return: dict
    """
    blog = model_to_dict(blog)
    if blog['content_urls'] != '':
        blog['content_urls'] = [tuple(url.strip().split(':::')) for url in blog['content_urls'].split('\n')]
    blog['content_tags'] = blog['content_tags'].split(',')
    if not process_content:
        return blog
    # Now, we should handle content text.
    # Enumerate every content type that is supported, raise a Http404 error if none of them matches.
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

    raise Http404()


def put_page_info(request, query_set, context):
    """
    Paginate a query set, get a slice of it (depending on the 'page' parameter of the request) and put it into the
    `blog` field of context. The `page` and `pcnt` field will also be updated.
    :param request: Request object.
    :param query_set: Result to be paged.
    :param context: Context to be updated.
    """
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404()  # Bad request if the parameter is not an integer
    context['blog'] = [blog_to_dict(blog, False) for blog in query_set[(page - 1) * 5:page * 5]]
    context['page'] = page
    context['pcnt'] = (len(query_set) + 4) // 5


@require_GET
def content(request, path):
    path = unquote('/'.join(path[:-1].split('/')))  # remove the trailing slash
    context = get_universal_context(path)
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
        put_page_info(request, query_set, context)
        # Because the template can not distinguish between normal index pages and search pages, we have to provide the
        # url for page navigation.
        context['rurl'] = request.path + '?'
        return render(request, 'blog-indices.html', context)


@require_GET
def indices(request):
    keyword = unquote(request.GET.get('keyword', ''))
    context = get_universal_context('', False)
    # The breadcrumb part needs extra handling.
    context['path'] = [('#', '搜索')]
    query_set = Blog.objects \
        .filter(Q(content_name__icontains=keyword) | Q(content_tags__icontains=keyword)) \
        .order_by('-publish_date')
    put_page_info(request, query_set, context)
    # This parameter is used to fill out the default value of the search bar.
    context['skey'] = keyword
    # Because the template can not distinguish between normal index pages and search pages, we have to provide the url
    # for page navigation.
    context['rurl'] = f'{request.path}?keyword={keyword}&'
    return render(request, 'blog-indices.html', context)


@login_required()
@user_passes_test(lambda u: u.is_superuser)
def publish(request):
    # Check the request method to distinguish between page requests and actual publishes.
    if request.method == 'GET':
        # The breadcrumb part needs extra handling, similar to indices.
        context = get_universal_context('', False)
        context['path'] = [('#', '发布')]
        # Add field 'stit' so that the edit option will not appear in the top-right menu again.
        context['stit'] = ''
        # Get an existing blog from database, if an id is given. Otherwise, this is creation, do nothing.
        if 'id' in request.GET:
            try:
                context.update(model_to_dict(Blog.objects.get(id=int(request.GET.get('id')))))
            except Blog.DoesNotExist or ValueError:
                raise Http404()
        else:
            # Set a default name to get rid of the ugly title
            context['content_name'] = '新增'
            # Set default date to current date
            context['publish_date'] = datetime.now()
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
        # Handle images first.
        # Validate the images first, if any of them is invalid, the whole publish request will not be handled.
        for image in request.FILES.getlist('images'):
            if image.size > 10485760:  # 10M
                return JsonResponse({'error': '图片' + image.name + '体积过大'})
        for image in request.FILES.getlist('images'):
            with open(os.path.join(settings.STATIC_ROOT, 'images', image.name), 'wb') as f:
                for chunk in image.chunks():
                    f.write(chunk)
        # Iterate through all fields and update them. It is guaranteed that the POST parameters' name is the same as
        # database columns.
        for field in Blog._meta.fields:
            if field.name != 'id':
                blog.__setattr__(field.name, request.POST.get(field.name, ''))
        blog.save()
        return redirect('blog-content', path=blog.publish_path + '/')  # the trailing slash is vital
