import re

from django import template
from django.conf import settings
from django.urls import reverse

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
    Create a paginator. Accept exactly three arguments: the current page number, the limit of one page, and the total
    number of pages.
    """
    if len(token.split_contents()) != 4:
        raise template.TemplateSyntaxError('%r tag requires exactly three arguments' % token.contents.split()[0])
    _, page, plim, pcnt = token.split_contents()
    page = parser.compile_filter(page)
    plim = parser.compile_filter(plim)
    pcnt = parser.compile_filter(pcnt)
    return PaginatorNode(page, plim, pcnt)


class NavigatorNode(template.Node):
    def __init__(self, nodelist_items, nodelist_links, nodelist_menus):
        self.nodelist_items, self.nodelist_links, self.nodelist_menus = nodelist_items, nodelist_links, nodelist_menus

    def render(self, context):
        if context.request.user.is_authenticated:
            if self.nodelist_menus is not None:
                html_user_menu = \
                    f'<div class="dropdown">' \
                    f'    <style>nav .dropdown-toggle:after{{content:none}}</style>' \
                    f'    <button class="btn btn-outline-info dropdown-toggle" data-toggle="dropdown" ' \
                    f'            aria-haspopup="true" aria-expanded="false">' \
                    f'        {context.request.user.username}' \
                    f'        &nbsp;&laquo;{context.request.user.email}&raquo;' \
                    f'    </button>' \
                    f'    <div class="dropdown-menu">' \
                    f'        {self.nodelist_menus.render(context)}' \
                    f'    </div>' \
                    f'</div>'
            else:
                html_user_menu = \
                    f'<button class="btn btn-outline-info">' \
                    f'    {context.request.user.username}' \
                    f'    &nbsp;&laquo;{context.request.user.email}&raquo;' \
                    f'</button>'
            # Determine what to display before navigator links.
            # A navigation through all supported applications is necessary if the user is a superuser, but it is
            # needless if the user is not, since non-superusers can access blogs only.
            if context.request.user.is_superuser:
                html_apps = \
                    f'<li class="nav-item">' \
                    f'    <a class="nav-link no-smooth" href="{reverse("blog-content", kwargs={"path": ""})}">' \
                    f'        博客' \
                    f'    </a>' \
                    f'</li>' \
                    f'<li class="nav-item">' \
                    f'    <a class="nav-link no-smooth" href="{reverse("logs")}">日志</a>' \
                    f'</li>' \
                    f'<li class="nav-item">' \
                    f'    <a class="nav-link no-smooth" href="{reverse("wcmd-wcui")}">命令行</a>' \
                    f'</li>' \
                    f'<li class="nav-item">' \
                    f'    <div class="navbar-text"' \
                    f'         style="border-left:1px solid darkgray;margin:0.5rem auto auto 0.3rem;height:1.5rem">' \
                    f'        &nbsp;' \
                    f'    </div>' \
                    f'</li>'
            else:
                html_apps = ''
        else:
            html_apps, html_user_menu = '', ''
        html = \
            f'<style>nav.fixed-top+div{{margin-top:4.5rem}}</style>' \
            f'<nav class="navbar fixed-top navbar-expand-lg navbar-light bg-light shadow" style="height:3.5rem">' \
            f'    <a class="navbar-brand no-smooth" href="/">' \
            f'        <img src="{settings.STATIC_URL + "home.png"}" alt="主页" style="height:3.5rem">' \
            f'    </a>' \
            f'    <div class="collapse navbar-collapse">' \
            f'        {self.nodelist_items.render(context) if self.nodelist_items else ""}' \
            f'        <ul class="navbar-nav mr-auto">' \
            f'            {html_apps}' \
            f'            {self.nodelist_links.render(context) if self.nodelist_links else ""}' \
            f'        </ul>' \
            f'        {html_user_menu}' \
            f'    </div>' \
            f'</nav>'
        return html


class PaginatorNode(template.Node):
    def __init__(self, page, plim, pcnt):
        self.page, self.plim, self.pcnt = page, plim, pcnt

    def render(self, context):
        def get_url(page_, limit_):
            url = context.request.get_full_path()
            url = re.sub(r'page=\d+', 'page=' + str(page_), url)
            url = re.sub(r'limit=\d+', 'limit=' + str(limit_), url)
            if '?' not in url:
                url += '?'
            if re.search(r'page=\d+', url) is None:
                url += ('&' if url[-1] != '&' else '') + 'page=' + str(page_) + '&'
            if re.search(r'limit=\d+', url) is None:
                url += ('&' if url[-1] != '&' else '') + 'limit=' + str(limit_) + '&'
            return url

        html_pages = ''
        page = self.page.resolve(context)
        plim = self.plim.resolve(context)
        pcnt = self.pcnt.resolve(context)
        for i in range(1, pcnt + 1):
            if i == page:
                html_pages += f'<li class="page-item active"><span class="page-link">{i}</span></li>'
            else:
                html_pages += \
                    f'<li class="page-item">' \
                    f'    <a class="page-link" href="{get_url(i, plim)}">{i}</a>' \
                    f'</li>'
        if page == 1:
            html_prev = \
                '<li class="page-item disabled">' \
                '    <span class="page-link"><span aria-hidden="true">&laquo;</span></span>' \
                '</li>'
        else:
            html_prev = \
                f'<li class="page-item">' \
                f'    <a class="page-link" href="{get_url(page - 1, plim)}">&laquo;</a>' \
                f'</li>'
        if page == pcnt:
            html_next = \
                '<li class="page-item disabled">' \
                '    <span class="page-link"><span aria-hidden="true">&raquo;</span></span>' \
                '</li>'
        else:
            html_next = \
                f'<li class="page-item">' \
                f'    <a class="page-link" href="{get_url(page + 1, plim)}">&raquo;</a>' \
                f'</li>'
        html = \
            f'<nav style="margin: auto">' \
            f'    <ul class="pagination">{html_prev}{html_pages}{html_next}</ul>' \
            f'</nav>'
        return html
