from urllib.parse import unquote

from django.forms import model_to_dict
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_GET
from markdown import Markdown

from blog.models import Blog

markdown = Markdown(extensions=['markdown.extensions.extra', 'markdown.extensions.toc'], slugify=slugify)


@require_GET
def display(request, _):
    # Get path and identify which blog to display
    path = unquote('/'.join(request.get_full_path().split('/')[2:-1]))
    blog = model_to_dict(get_object_or_404(Blog, publish_path=path))

    # Process breadcrumb
    href, path = '/blog/', path.split('/')
    for i in range(len(path)):
        href, path[i] = href + path[i] + '/', (href + path[i] + '/', path[i])
    blog['path'] = path

    # Process url links
    blog['content_urls'] = [tuple(tag.split(';')) for tag in blog['content_urls'].split(',')]

    # Process tags
    blog['content_tags'] = blog['content_tags'].split(',')  # TODO add href to tags

    # Process content text according to its type
    if blog['content_type'] == 'markdown':
        blog['content_text'] = markdown.convert(blog['content_text'])
        # The official TOC plugin is disgusting, so we do by ourselves. We do not want too much nesting lists since
        # it will cause line wrapping, so we collect two levels of headers only. Since <h1> is the main title of the
        # article and is meaningless to put it in TOC, we should collect <h2> and <h3> only.

        # Every item of the generated TOC list is a tuple of two elements: the first is the title (i.e the text to be
        # displayed), the second is the html target's id. If the first element if none, it implies that the second
        # element is a list representing the inner TOC (<h3>). There are at most two layers.

        # TODO this may be slow since it will iterate the whole document, some sort of caching can be added
        toc = []
        for i in range(len(blog['content_text']) - 3):
            if blog['content_text'][i:i + 3] == '<h2':
                # The next eight characters must be '<h2 id="', so the position of the first '"' from the ninth
                # character is the end of id.
                href_end = i + 8 + blog['content_text'][i + 8:].index('"')
                # After then, the fist '</h2>' is the end of what should be displayed. Remember that the '">' after href
                # should be jumped over.
                name_end = href_end + blog['content_text'][href_end:].index('</h2>')
                toc.append((blog['content_text'][href_end + 2:name_end], blog['content_text'][i + 8:href_end]))
            if blog['content_text'][i:i + 3] == '<h3':
                # The logic here is similar to <h2>.
                href_end = i + 8 + blog['content_text'][i + 8:].index('"')
                name_end = href_end + blog['content_text'][href_end:].index('</h3>')
                # If the last item of the list is also a nested layer, we should append the current navigation to that
                # layer, instead of creating a new one.
                if len(toc) > 0 and toc[-1][0] is None:
                    toc[-1][1].append(
                        (blog['content_text'][href_end + 2:name_end], blog['content_text'][i + 8:href_end]))
                else:
                    toc.append(
                        (None, [(blog['content_text'][href_end + 2:name_end], blog['content_text'][i + 8:href_end])]))
        blog['content_toc'] = toc
        return render(request, 'blog-markdown.html', blog)
