from django import template
from django.urls import reverse

register = template.Library()


@register.tag('sidecard')
def do_side_card(parser, token):
    """
    Create a card which suits perfectly in the sidebar. Accept one and only one argument, which is the title of the
    card.
    This tag should be ended with `endsidecard`.
    """
    try:
        _, title = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires exactly one argument" % token.contents.split()[0])
    body = parser.parse(('endsidecard',))
    parser.delete_first_token()
    return SideCardNode(parser.compile_filter(title), body)


@register.tag('tag')
def do_tag(parser, token):
    """
    Crate a tag. Accept at most two arguments, the first one must be the tag text, and the second one (if presented)
    must be `nolink` indicating that the tag is not displayed in an <a> but a <div>.
    """
    bits = token.split_contents()
    if len(bits) != 2 and len(bits) != 3:
        raise template.TemplateSyntaxError("%r tag requires one or two arguments" % token.contents.split()[0])
    if len(bits) == 3 and bits[-1] != 'nolink':
        raise template.TemplateSyntaxError("wrong last argument for %r tag" % token.contents.split()[0])
    return TagNode(parser.compile_filter(bits[1]), len(bits) == 3)


@register.tag('date')
def do_date(parser, token):
    """
    Create a publish date text representation, along with publish description text.
    """
    bits = token.split_contents()
    if len(bits) != 2 and len(bits) != 3:
        raise template.TemplateSyntaxError("%r tag requires one or two arguments" % token.contents.split()[0])
    date = parser.compile_filter(bits[1])
    desc = parser.compile_filter(bits[2]) if len(bits) == 3 else parser.compile_filter('""')
    return DateNode(date, desc)


class SideCardNode(template.Node):
    def __init__(self, title, body):
        self.title, self.body = title, body

    def render(self, context):
        return f'<div class="card shadow mb-3"><div class="card-body">' \
               f'<div class="markdown-body mb-3"><h2>{self.title.resolve(context)}</h2></div>' \
               f'{self.body.render(context)}' \
               f'</div></div>'


class TagNode(template.Node):
    def __init__(self, tag, nolink):
        self.tag, self.nolink = tag, nolink

    def render(self, context):
        tag = self.tag.resolve(context)
        if self.nolink:
            return f'<div class="badge badge-secondary">{tag}</div>&nbsp;'
        else:
            return f'<a href="{reverse("blog-indices")}?keyword={tag}" class="badge badge-secondary">{tag}</a>&nbsp;'


class DateNode(template.Node):
    def __init__(self, date, desc):
        self.date, self.desc = date, desc

    def render(self, context):
        date = self.date.resolve(context)
        desc = self.desc.resolve(context)
        return f'<div class="text-muted text-right"><span>' \
               f'{date.strftime("%Y-%m-%d")}' + (f'，{desc}' if desc != '' else '') + \
               '</div></span>'
