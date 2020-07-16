import os
import re
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test, login_required
from django.forms import model_to_dict
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from markdown import Markdown

from blog.models import Blog

markdown = Markdown(extensions=['markdown.extensions.extra', 'markdown.extensions.toc', 'arithmatex'],
                    extension_configs={
                        # Enable generic mode for katex, disable smart dollar because it breaks inline math.
                        'arithmatex': {'generic': True, 'smart_dollar': False}
                    },
                    # They said that this can help to improve Chinese character issues.
                    slugify=slugify)


def get_universal_context(path):
    """
    Get category list, tags and recent articles which are used in any circumstances. Will also split and process path
    string into a list consisting of link href and title, in order to generate information required by breadcrumb.
    :param path: The path string
    :return A default context.
    :rtype dict
    """
    # collect categories (the first directory of publish path) and tags.
    categories, tags = set(), set()
    for blog in Blog.objects.all().only('publish_path', 'content_tags'):
        categories.add(blog.publish_path.split('/')[0])
        for tag in blog.content_tags.split(','):
            tags.add(tag)

    # Collect 5 recent articles.
    query_set = Blog.objects.all().order_by('-publish_date').only('publish_path', 'publish_date', 'content_name')
    query_set = query_set[:min(5, len(query_set))]
    recent = [(blog.content_name, blog.publish_date, blog.publish_path) for blog in query_set]

    # Parse requested path. If the path is empty, return an empty string instead.
    if len(path) > 0:
        href, path = '', path.split('/')
        for i in range(len(path)):
            href, path[i] = href + path[i] + '/', (href + path[i] + '/', path[i])

    return {'cate': categories, 'tags': tags, 'rect': recent, 'path': path}


def get_cover_image(blog):
    """
    Get a cover image from a blog object.
    :param blog: Blog object.
    :return: The url (not including static path) of the cover image.
    :rtype: str
    """
    # Simply select the first image throughout the content which has the correct alt text.
    if blog.content_type == 'markdown':
        result = re.search(r'!\[cover]\(([-/\w]+\.(png|jpg|jpeg|gif|svg))\)', blog.content_text)
        if result is not None:
            return result.group(1)

    # In case of there are no images in the content (or that the content type is unrecognizable), we use the category
    # image as the cover.
    return os.path.join(settings.STATIC_URL, 'images', blog.publish_path.split('/')[0] + '.png')


def get_index_context(blog):
    """
    Get the dictionary form of a blog object to be displayed on an index page.
    :param blog: Blog object.
    :return: Similar to model_to_dict but some unnecessary fields omitted.
    :rtype: dict
    """
    return {
        'publish_path': blog.publish_path,
        'publish_date': blog.publish_date,
        'publish_desc': blog.publish_desc,
        'content_cimg': get_cover_image(blog),
        'content_name': blog.content_name,
        'content_desc': blog.content_desc,
        'content_tags': blog.content_tags.split(',')
    }


def put_page_info(request, query_set, context):
    """
    Put pagination info into the context.
    :param request: Request object.
    :param query_set: Result to be paged.
    :param context: Context to be updated.
    """
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404()  # Bad request if the parameter is not an integer
    context['page'] = page
    context['pcnt'] = (len(query_set) + 4) // 5
    context['blog'] = [get_index_context(blog) for blog in query_set[(page - 1) * 5:page * 5]]


# noinspection PyTypeChecker
@require_GET
def content(request, path):
    path = unquote('/'.join(path[:-1].split('/')))
    context = get_universal_context(path)

    try:
        context.update(model_to_dict(Blog.objects.get(publish_path=path)))
    except Blog.DoesNotExist:
        # If the blog specified by this path does not exists, then check if there are any blogs under this directory. If
        # yes, display an index page. Otherwise, return 404.
        query_set = Blog.objects.filter(publish_path__startswith=path)
        # Note that empty path (i.e. root) will never raise 404, otherwise there will be no entrance if no blogs online.
        if len(query_set) == 0 and path != '':
            raise Http404()
        put_page_info(request, query_set, context)

        # Because the template can not distinguish between normal index pages and search pages, we have to provide the
        # url for page navigation.
        context['rurl'] = request.path + '?'

        return render(request, 'blog-indices.html', context)

    # Process url links and tags
    context['content_urls'] = [tuple(tag.split(';')) for tag in context['content_urls'].split(',')]
    context['content_tags'] = context['content_tags'].split(',')

    # Process content text according to its type
    if context['content_type'] == 'markdown':
        context['content_text'] = markdown.convert(context['content_text'])
        # The official TOC plugin is disgusting, so we do by ourselves. We do not want too much nesting lists since
        # it will cause line wrapping, so we collect two levels of headers only. Since <h1> is the main title of the
        # article and is meaningless to put it in TOC, we should collect <h2> and <h3> only.

        # Every item of the generated TOC list is a tuple of two elements: the first is the title (i.e the text to be
        # displayed), the second is the html target's id. If the first element if none, it implies that the second
        # element is a list representing the inner TOC (<h3>). There are at most two layers.

        # TODO this may be slow since it will iterate the whole document, some sort of caching can be added
        toc = []
        for i in range(len(context['content_text']) - 3):
            if context['content_text'][i:i + 3] == '<h2':
                # The next eight characters must be '<h2 id="', so the position of the first '"' from the ninth
                # character is the end of id.
                href_end = i + 8 + context['content_text'][i + 8:].index('"')
                # After then, the fist '</h2>' is the end of what should be displayed. Remember that the '">' after href
                # should be jumped over.
                name_end = href_end + context['content_text'][href_end:].index('</h2>')
                toc.append((context['content_text'][href_end + 2:name_end], context['content_text'][i + 8:href_end]))

            if context['content_text'][i:i + 3] == '<h3':
                # The logic here is similar to <h2>.
                href_end = i + 8 + context['content_text'][i + 8:].index('"')
                name_end = href_end + context['content_text'][href_end:].index('</h3>')
                # If the last item of the list is also a nested layer, we should append the current navigation to that
                # layer, instead of creating a new one.
                if len(toc) > 0 and toc[-1][0] is None:
                    toc[-1][1].append(
                        (context['content_text'][href_end + 2:name_end], context['content_text'][i + 8:href_end]))
                else:
                    toc.append(
                        (None,
                         [(context['content_text'][href_end + 2:name_end], context['content_text'][i + 8:href_end])]))
        context['content_toc'] = toc

        return render(request, 'blog-content.html', context)

    # TODO add return statement when content type is not recognizable


@login_required()
@user_passes_test(lambda u: u.is_superuser)
@require_POST
@csrf_exempt
def add_img(request):
    # Validate the images first, if any of them is invalid, the whole batch will not be saved.
    for image in request.FILES.getlist('file_data'):
        if image.size > 10485760:  # 10M
            return JsonResponse({'error': '图片' + image.name + '体积过大'})

    for image in request.FILES.getlist('file_data'):
        with open(os.path.join(settings.STATIC_ROOT, 'images', image.name), 'wb') as f:
            for chunk in image.chunks():
                f.write(chunk)
    return JsonResponse({})


@require_GET
def indices(request):
    # Unquote possible Chinese characters.
    title, tag = unquote(request.GET.get('title', '')), unquote(request.GET.get('tag', ''))

    # The breadcrumb part needs extra handling.
    context = get_universal_context('')
    context['path'] = [('#', '搜索')]

    query_set = Blog.objects.filter(content_name__icontains=title, content_tags__contains=tag).order_by('-publish_date')
    put_page_info(request, query_set, context)

    # These two parameters are used to fill out the default value of the search bar.
    context['stit'] = title
    context['stag'] = tag

    # Because the template can not distinguish between normal index pages and search pages, we have to provide the url
    # for page navigation.
    context['rurl'] = f'{request.path}?title={title}&tag={tag}&'

    return render(request, 'blog-indices.html', context)


@login_required()
@user_passes_test(lambda u: u.is_superuser)
def publish(request):
    if request.method == 'GET':
        # The breadcrumb part needs extra handling, similar to indices.
        context = get_universal_context('')
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
        # Iterate through all fields and update them. It is guaranteed that the POST parameters' name is the same as
        # database columns.
        for field in Blog._meta.fields:
            if field.name != 'id':
                blog.__setattr__(field.name, request.POST.get(field.name, ''))
        blog.save()
        return redirect('/blog/' + blog.publish_path)  # TODO reverse won't work, don't know why
