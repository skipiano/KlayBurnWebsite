from django.shortcuts import render
from .models import Member, BlockData, TransactionData, GasFeeData
from django.views import generic
import matplotlib
import matplotlib.pyplot as plt
import io
import base64
matplotlib.use('Agg')


class BlockView(generic.ListView):
    model = Member


def index(request):

    context = {}

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


def block_member(request, pk):
    try:
        context = {}
        member = Member.objects.get(pk=pk)
        # debug
        plt.plot([0, 1, 2, 3, 4], [0, 3, 5, 9, 11])
        plt.xlabel('Months')
        plt.ylabel('Books Read')
        flike = io.BytesIO()
        plt.savefig(flike)
        b64 = base64.b64encode(flike.getvalue()).decode()
        context['chart_all'] = b64
        plt.close()

    except Member.DoesNotExist:
        raise Http404('Member does not exist')

    return render(request, 'index/graph.html', context=context)


def transaction(request):
    # debug
    context = {}
    plt.plot([0, 1, 2, 3, 4], [11, 9, 5, 3, 0])
    plt.xlabel('Months')
    plt.ylabel('Books Read')
    flike = io.BytesIO()
    plt.savefig(flike)
    b64 = base64.b64encode(flike.getvalue()).decode()
    context['chart_all'] = b64
    plt.close()

    return render(request, 'index/graph_csv.html', context=context)


def gas_fee(request):

    return render(request, 'index/graph_csv.html')
