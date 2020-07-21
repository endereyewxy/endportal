from django.http import Http404


def paginate(request, query_set):
    """
    Get pagination information from a request object and return the correct slice of a query set.
    The page number is defined by the `page` field of GET parameters (default value one), while the number of pages is
    defined by the `limit` field of GET parameters (default value five). 404 error will be raised if any of the two
    parameters is not an integer.
    :param request: Request object used to fetch pagination information.
    :param query_set: Query set to be sliced.
    :return: Pagination information and a sliced query set.
    :rtype int, int, int, QuerySet
    """
    try:
        page, limit = int(request.GET.get('page', 1)), int(request.GET.get('limit', 5))
    except ValueError:
        raise Http404
    return page, limit, len(query_set) // limit, query_set[(page - 1) * limit: page * limit]
