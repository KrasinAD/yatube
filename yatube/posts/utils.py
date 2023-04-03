from django.core.paginator import Paginator

COUNT_POST: int = 10


def paginator(request, post_list):
    paginator = Paginator(post_list, COUNT_POST)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
