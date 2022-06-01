from django.shortcuts import render
from .models import Member, BlockData, TransactionData, GasFeeData
from django.views import generic
import matplotlib
import matplotlib.pyplot as plt
import io
import base64
import datetime
import pandas as pd
import csv
from django.utils.encoding import smart_str
from django.urls import reverse
from django.http import HttpResponse
matplotlib.use('Agg')


class BlockView(generic.ListView):
    model = Member


def index(request):

    context = {}

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


def block_member(request, pk):
    try:
        member = Member.objects.get(pk=pk)
        block_data = [blocks for blocks in BlockData.objects.filter(
            member__exact=member)]
        block_amount_data = [blocks.amount for blocks in BlockData.objects.filter(
            member__exact=member)]
        end_date = block_data[-1].date
        context = define_context(block_amount_data,
                                 end_date, member.name + " Blocks", "Blocks", "block-download")
    except Member.DoesNotExist:
        raise Http404('Member does not exist')

    return render(request, 'index/graph.html', context=context)


def transaction(request):
    transaction_data = [
        transaction for transaction in TransactionData.objects.all()]
    transaction_amount_data = [
        transaction.amount for transaction in TransactionData.objects.all()]
    end_date = transaction_data[-1].date
    context = define_context(transaction_amount_data,
                             end_date, "Transactions", "Transactions", "transaction-download")

    return render(request, 'index/graph_csv.html', context=context)


def gas_fee(request):
    gas_data = [
        gas for gas in GasFeeData.objects.all()]
    gas_amount_data = [
        gas.amount for gas in GasFeeData.objects.all()]
    end_date = gas_data[-1].date
    context = define_context(gas_amount_data,
                             end_date, "Gas Fees", "Gas ($KLAY)", "gas-download")
    return render(request, 'index/graph_csv.html', context=context)


def encode_graph(data, start_date, end_date, start_ind, label):
    fig, ax = plt.subplots()
    ax.plot(pd.Series(data[start_ind:], index=pd.date_range(
        start_date, end_date)))
    ax.set_xlabel('Date')
    ax.set_ylabel(label)
    fig.autofmt_xdate()
    fig.tight_layout()
    flike = io.BytesIO()
    fig.savefig(flike, dpi=300)
    plt.close()
    return base64.b64encode(flike.getvalue()).decode()


def define_context(data, end_date, title, label, download):
    context = {}
    start_all_date = datetime.datetime(2019, 6, 25)
    start_year_date = end_date - datetime.timedelta(days=365)
    start_month_date = end_date - datetime.timedelta(days=30)
    context['chart_all'] = encode_graph(
        data, start_all_date, end_date, 0, label)
    context['chart_year'] = encode_graph(
        data, start_year_date, end_date, -366, label)
    context['chart_month'] = encode_graph(
        data, start_month_date, end_date, -31, label)
    context['title'] = title
    context['download'] = reverse(download)
    return context


def block_download(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="blocks.csv"'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    headers = [smart_str(u"Date")]
    for member in Member.objects.all():
        headers.append(smart_str(member.name))
    writer.writerow(headers)
    start_date = datetime.date(2019, 6, 25)
    block_data = [blocks for blocks in BlockData.objects.filter(
        member__exact=member)]
    end_date = block_data[-1].date
    while start_date <= end_date:
        row = [smart_str(start_date)] + [smart_str(blocks.amount)
                                         for blocks in BlockData.objects.filter(date__exact=start_date)]
        writer.writerow(row)
        start_date = start_date + datetime.timedelta(days=1)
    return response


def transaction_download(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([smart_str(u"Date"), smart_str(u"Transactions")])
    for tx in TransactionData.objects.all():
        writer.writerow([smart_str(tx.date), smart_str(tx.amount)])
    return response


def gas_fee_download(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="gas_fees.csv"'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([smart_str(u"Date"), smart_str(u"Gas ($KLAY)")])
    for tx in GasFeeData.objects.all():
        writer.writerow([smart_str(tx.date), smart_str(tx.amount)])
    return response
