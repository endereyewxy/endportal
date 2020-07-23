import re

from django import template
from django.conf import settings

register = template.Library()


@register.tag('navigator')
def do_navigator(parser, token):
    """
    Create a navigator fixed at the top of the window. Home page icon, available apps and user menu are automatically
    configured and added Accept no arguments.
    Usage:
    ```
    {% navigator %}
        {# Things to put before the links. #}
        {% links %}
        <li class="nav-item">
            <a class="nav-link" href="#href">A simple navbar link</a>
        </li>
        {# Some other links. #}
        {% menus %}
        <a class="dropdown-item" href="#href">
            A simple user menu option.
        </a>
        {# Some other options. #}
    {% endnavigator %}
    ```
    """
    if len(token.split_contents()) != 1:
        raise template.TemplateSyntaxError('%r tag requires no arguments' % token.contents.split()[0])
    nodelist_items = parser.parse(('links', 'menus', 'endnavigator'))
    token = parser.next_token()
    if token.contents == 'links':
        nodelist_links = parser.parse(('menus', 'endnavigator'))
        token = parser.next_token()
    else:
        nodelist_links = None
    if token.contents == 'menus':
        nodelist_menus = parser.parse(('endnavigator',))
        parser.delete_first_token()
    else:
        nodelist_menus = None
    return NavigatorNode(nodelist_items, nodelist_links, nodelist_menus)


@register.tag('paginator')
def do_paginator(parser, token):
    """
    Create a paginator. Accept exactly two arguments: the current page number and the total number of pages.
    """
    if len(token.split_contents()) != 3:
        raise template.TemplateSyntaxError('%r tag requires exactly two arguments' % token.contents.split()[0])
    _, page, pcnt = token.split_contents()
    page = parser.compile_filter(page)
    pcnt = parser.compile_filter(pcnt)
    return PaginatorNode(page, pcnt)


@register.tag('footer')
def do_footer(_, token):
    """
    Create a footer containing a github link and domain registration information. Take no arguments.
    """
    if len(token.split_contents()) != 1:
        raise template.TemplateSyntaxError('%r tag requires no arguments' % token.contents.split()[0])
    return FooterNode()


class NavigatorNode(template.Node):
    def __init__(self, nodelist_items, nodelist_links, nodelist_menus):
        self.nodelist_items, self.nodelist_links, self.nodelist_menus = nodelist_items, nodelist_links, nodelist_menus

    def render(self, context):
        # Custom user menus are only displayed if the user is authenticated.
        if context.request.user.is_authenticated:
            if self.nodelist_menus is not None:
                html_user_menu = \
                    f'<div class="nav-item dropdown">' \
                    f'    <a aria-expanded="false" class="nav-link text-secondary dropdown-toggle"' \
                    f'       data-toggle="dropdown" href="#" role="button">' \
                    f'        {context.request.user.username}&nbsp;&laquo;{context.request.user.email}&raquo;' \
                    f'    </a>' \
                    f'    <ul class="dropdown-menu dropdown-menu-right">' \
                    f'        {self.nodelist_menus.render(context)}' \
                    f'    </ul>' \
                    f'</div>'
            else:
                html_user_menu = \
                    f'<span class="navbar-text">' \
                    f'    {context.request.user.username}&nbsp;&laquo;{context.request.user.email}&raquo;' \
                    f'</span>'
        else:
            html_user_menu = ''
        html = \
            f'<style>nav.fixed-top+div{{margin-top:4.5rem}}</style>' \
            f'<nav class="navbar fixed-top navbar-expand-lg navbar-light bg-light shadow" style="height:3.5rem">' \
            f'    <div class="container-fluid">' \
            f'        <a class="navbar-brand no-smooth" href="/">' \
            f'            <img alt="主页" src="{settings.STATIC_URL + "home.png"}" style="height:3.5rem">' \
            f'        </a>' \
            f'        <div class="collapse navbar-collapse">' \
            f'            {self.nodelist_items.render(context) if self.nodelist_items else ""}' \
            f'            <ul class="navbar-nav ml-2 mr-auto">' \
            f'                {self.nodelist_links.render(context) if self.nodelist_links else ""}' \
            f'            </ul>' \
            f'            {html_user_menu}' \
            f'        </div>' \
            f'    </div>' \
            f'</nav>'
        return html


class PaginatorNode(template.Node):
    def __init__(self, page, pcnt):
        self.page, self.pcnt = page, pcnt

    def render(self, context):
        def get_url(page_):
            """
            Get the corresponding navigation url according to target page and limit.
            :param page_: Target page number.
            :return: Corresponding url.
            :rtype str
            """
            url = context.request.get_full_path()
            # Replace old GET parameters into correct ones.
            url = re.sub(r'page=\d+', 'page=' + str(page_), url)
            # Add the question mark if the original url has no GET parameters.
            if '?' not in url:
                url += '?'
            # Add parameters if the original url does not have them. Do not forget to add the `&` if the original url
            # does not end with that.
            if re.search(r'page=\d+', url) is None:
                url += ('&' if url[-1] != '&' else '') + 'page=' + str(page_) + '&'
            return url

        html_pages = ''
        page = self.page.resolve(context)
        pcnt = self.pcnt.resolve(context)
        # Handle the middle part of the paginator. where users can click on numbers to jump to the corresponding page.
        for i in range(1, pcnt + 1):
            if i == page:
                html_pages += f'<li class="page-item active"><span class="page-link">{i}</span></li>'
            else:
                html_pages += \
                    f'<li class="page-item">' \
                    f'    <a class="page-link" href="{get_url(i)}">{i}</a>' \
                    f'</li>'
        # Handle previous page button.
        if page == 1:
            html_prev = \
                '<li class="page-item disabled">' \
                '    <span class="page-link"><span aria-hidden="true">&laquo;</span></span>' \
                '</li>'
        else:
            html_prev = \
                f'<li class="page-item">' \
                f'    <a class="page-link" href="{get_url(page - 1)}">&laquo;</a>' \
                f'</li>'
        # Handle next page button.
        if page == pcnt:
            html_next = \
                '<li class="page-item disabled">' \
                '    <span class="page-link"><span aria-hidden="true">&raquo;</span></span>' \
                '</li>'
        else:
            html_next = \
                f'<li class="page-item">' \
                f'    <a class="page-link" href="{get_url(page + 1)}">&raquo;</a>' \
                f'</li>'
        html = \
            f'<nav>' \
            f'    <ul class="pagination justify-content-center">{html_prev}{html_pages}{html_next}</ul>' \
            f'</nav>'
        return html


class FooterNode(template.Node):
    def render(self, context):
        return \
            f'<div class="footer">' \
            f'    <hr style="margin:auto;margin-bottom:1rem;width:75vw">' \
            f'    <div class="text-center w-100">' \
            f'        <p>' \
            f'            <svg height="1.5rem" viewBox="0 0 24 24" width="1.5rem" xmlns="http://www.w3.org/2000/svg">' \
            f'                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 ' \
            f'11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333' \
            f'-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 ' \
            f'3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 ' \
            f'1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 ' \
            f'1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 ' \
            f'1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 ' \
            f'.319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"></path>' \
            f'            </svg>' \
            f'            <a class="text-muted text-decoration-none align-middle" href="https://github.com/endereye">' \
            f'                访问Github' \
            f'            </a>' \
            f'        </p>' \
            f'    </div>' \
            f'</div>'
