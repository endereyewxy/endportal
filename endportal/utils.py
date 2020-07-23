from django.http import Http404


def paginate(request, limit, query_set):
    """
    Get pagination information from a request object and return the correct slice of a query set. The page number is
    defined by the `page` field of GET parameters (default value one). 404 error will be raised if any of the two
    parameters is not an integer.
    :param request: Request object used to fetch pagination information.
    :param limit: The number of records per page.
    :param query_set: Query set to be sliced.
    :return: Pagination information and a sliced query set.
    :rtype int, int, int, QuerySet
    """
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404
    return page, limit, (len(query_set) + limit - 1) // limit, query_set[(page - 1) * limit: page * limit]
