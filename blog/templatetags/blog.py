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


@register.tag('blog_tag')
def do_blog_tag(parser, token):
    """
    Crate a tag. Accept at most two arguments, the first one must be the tag text, and the second one (if presented)
    must be `nolink` indicating that the tag is not displayed in an <a> but a <div>.
    """
    bits = token.split_contents()
    if len(bits) != 2 and len(bits) != 3:
        raise template.TemplateSyntaxError("%r tag requires one or two arguments" % token.contents.split()[0])
    if len(bits) == 3 and bits[-1] != 'nolink':
        raise template.TemplateSyntaxError("wrong last argument for %r tag" % token.contents.split()[0])
    return BlogTagNode(parser.compile_filter(bits[1]), len(bits) == 3)


@register.tag('publish_date')
def do_publish_date(parser, token):
    """
    Create a publish date text representation, along with publish description text, if presented. Accept one or two
    arguments, which is the date and description of publish, respectively.
    """
    bits = token.split_contents()
    if len(bits) != 2 and len(bits) != 3:
        raise template.TemplateSyntaxError("%r tag requires one or two arguments" % token.contents.split()[0])
    date = parser.compile_filter(bits[1])
    desc = parser.compile_filter(bits[2]) if len(bits) == 3 else parser.compile_filter('""')
    return PublishDateNode(date, desc)


class SideCardNode(template.Node):
    def __init__(self, title, body):
        self.title, self.body = title, body

    def render(self, context):
        return \
            f'<div class="card shadow mb-3">' \
            f'   <div class="card-body">' \
            f'       <div class="markdown-body mb-3">' \
            f'           <h2>{self.title.resolve(context)}</h2>' \
            f'       </div>' \
            f'       {self.body.render(context)}' \
            f'   </div>' \
            f'</div>'


class BlogTagNode(template.Node):
    def __init__(self, tag, nolink):
        self.tag, self.nolink = tag, nolink

    def render(self, context):
        tag = self.tag.resolve(context)
        if self.nolink:
            return f'<div class="badge badge-secondary">{tag}</div>'
        else:
            return f'<a href="{reverse("blog-indices")}?keyword={tag}" class="badge badge-secondary">{tag}</a>'


class PublishDateNode(template.Node):
    def __init__(self, date, desc):
        self.date, self.desc = date, desc

    def render(self, context):
        date = self.date.resolve(context)
        desc = self.desc.resolve(context)
        return \
            f'<div class="text-muted text-right">' \
            f'   <span>{date.strftime("%Y-%m-%d")}' + (f'，{desc}' if desc != '' else '') + '</span>' + \
            f'</div>'
