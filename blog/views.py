import re
from urllib.parse import unquote

from django.forms import model_to_dict
from django.http import Http404
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.http import require_GET
from markdown import Markdown

from blog.models import Blog

markdown = Markdown(extensions=['markdown.extensions.extra', 'markdown.extensions.toc'], slugify=slugify)


def get_universal_context(path):
    """
    Get category list, tags and recent articles which are used in any circumstances. Will also split and process path
    string into a list consisting of link href and title, in order to generate information required by breadcrumb.
    :param path: The path string
    :return A default context.
    :rtype dict
    """
    categories, tags = set(), set()
    for blog in Blog.objects.all().only('publish_path', 'content_tags'):
        categories.add(blog.publish_path.split('/')[0])
        for tag in blog.content_tags.split(','):
            tags.add(tag)
    recent = [(blog.content_name, blog.publish_date, blog.publish_path) for blog in
              Blog.objects.all().order_by('-publish_date').only('publish_path', 'publish_date', 'content_name')[:5]]
    href, path = '/blog/', path.split('/')
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
    # Simply select the first image throughout the content
    if blog.content_type == 'markdown':
        result = re.search(r'!\[\w*\]\(([-/\w]+\.(png|jpg|jpeg|gif|svg))\)', blog.content_text)
        if result is not None:
            return result.group(1)

    # In case of there are no images in the content (or that the content type is unrecognizable), we use the category
    # image as the cover.
    return '/static/images/' + blog.publish_path.split('/')[0] + '.jpg'


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


# noinspection PyTypeChecker
@require_GET
def display(request, path):
    path = unquote('/'.join(path[:-1].split('/')))
    context = get_universal_context(path)

    try:
        context.update(model_to_dict(Blog.objects.get(publish_path=path)))
    except Blog.DoesNotExist:
        # If the blog specified by this path does not exists, then check if there are any blogs under this directory. If
        # yes, display an index page. Otherwise, return 404.
        query_set = Blog.objects.filter(publish_path__startswith=path)
        if len(query_set) == 0:
            raise Http404()
            # Some fields are not required.
        context['blog'] = [get_index_context(blog) for blog in query_set]
        return render(request, 'blog-index.html', context)

    # Process url links
    context['content_urls'] = [tuple(tag.split(';')) for tag in context['content_urls'].split(',')]

    # Process tags
    context['content_tags'] = context['content_tags'].split(',')  # TODO add href to tags

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
        return render(request, 'blog-markdown.html', context)


@require_GET
def search(request):
    title, tag = request.GET.get('title', ''), request.GET.get('tag', '')

    # The breadcrumb part needs extra handling.
    context = get_universal_context('')
    context['path'] = [('#', '搜索')]

    context['stit'] = title
    context['blog'] = [get_index_context(blog) for blog in
                       Blog.objects
                           .filter(content_name__icontains=title, content_tags__contains=tag)
                           .order_by('-publish_date')]
    return render(request, 'blog-index.html', context)
