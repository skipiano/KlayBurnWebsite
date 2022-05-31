from django.shortcuts import render
from .models import Member
from django.views import generic


class BlockView(generic.ListView):
    model = Member


def index(request):

    context = {}

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


def block_member(request, pk):
    try:
        member = Member.objects.get(pk=pk)

    except Member.DoesNotExist:
        raise Http404('Member does not exist')

    return render(request, 'index/graph.html')


def transaction(request):

    return render(request, 'index/graph.html')


def gas_fee(request):

    return render(request, 'index/graph.html')
