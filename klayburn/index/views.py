from django.shortcuts import render
from .models import Member, BlockData, TransactionData, GasFeeData
from django.views import generic
import matplotlib
import matplotlib.pyplot as plt
import io
from io import StringIO
import base64
import datetime
import numpy as np
import pandas as pd
import csv
from django.utils.encoding import smart_str
from django.urls import reverse
from django.http import HttpResponse
import requests
import time
from dateutil.relativedelta import relativedelta

matplotlib.use('Agg')
_data = []


class BlockView(generic.ListView):
    model = Member


def index(request):

    context = {}

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


def block_member(request, pk):
    try:
        member = Member.objects.get(pk=pk)
        block_amount_data = [blocks.amount for blocks in BlockData.objects.filter(
            member__exact=member)]
        end_date = get_end_date()
        context = define_context(block_amount_data,
                                 end_date, member.name + " Blocks", "Blocks", "block-download")
    except Member.DoesNotExist:
        raise Http404('Member does not exist')

    return render(request, 'index/graph.html', context=context)


def transaction(request):
    transaction_amount_data = [
        transaction.amount for transaction in TransactionData.objects.all()]
    end_date = get_end_date()
    context = define_context(transaction_amount_data,
                             end_date, "Transactions", "Transactions", "transaction-download")

    return render(request, 'index/graph_csv.html', context=context)


def gas_fee(request):
    gas_amount_data = [
        gas.amount for gas in GasFeeData.objects.all()]
    end_date = get_end_date()
    context = define_context(gas_amount_data,
                             end_date, "Gas Fees", "Gas ($KLAY)", "gas-download")
    return render(request, 'index/graph_csv.html', context=context)


def encode_graph(data, start_date, end_date, start_ind, label):
    fig, ax = plt.subplots()
    ax.plot(pd.Series(data[start_ind:], index=pd.date_range(
        start_date, end_date)))
    ax.set_yscale('log')
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


def update(request):
    starting_time = time.time()
    start_date = get_end_date()+datetime.timedelta(days=1)
    end_date = datetime.date.today()-datetime.timedelta(days=1)
    if start_date <= end_date:
        start_month = datetime.datetime(start_date.year, start_date.month, 1)
        end_month = datetime.datetime(end_date.year, end_date.month, 1)
        date_delta = end_date - start_date
        num_days = date_delta.days + 1
        block_list_dict = {}
        for member in Member.objects.all():
            block_list_dict[member.name] = np.zeros(num_days, dtype=np.uint32)
        transaction_list = np.zeros(num_days, dtype=np.uint64)
        gas_fee_list = np.zeros(num_days)
        head = {"referer": "https://scope.klaytn.com/"}
        request_link1 = "https://api-cypress-v2.scope.klaytn.com/v2/accounts/"
        request_link2 = "/blocks/download?date="
        while start_month <= end_month:
            print(datetime.datetime.strftime(start_month, "%Y-%m"))
            # load all of the csv files for a KGC member, then iterate over
            for member in Member.objects.all():
                print(member.name)
                try:
                    if not member.active:
                        continue
                    response = requests.get(
                        request_link1 + member.address + request_link2 + datetime.datetime.strftime(start_month, "%Y-%m"), headers=head)
                    if response.text and response.text[0] != "<":
                        df = pd.read_csv(StringIO(response.text),
                                         usecols=[1, 2, 3])
                        df.apply(lambda row: collect_data_from_row(
                            row, block_list_dict, transaction_list, gas_fee_list, start_date, member.name), axis=1)
                except Exception:
                    pass
            start_month = start_month + relativedelta(months=1)
        print(block_list_dict)
        print(transaction_list)
        print(gas_fee_list)
        for i in range(num_days):
            cur_date = start_date+datetime.timedelta(days=i)
            for member in Member.objects.all():
                BlockData.objects.create(
                    member=member, date=cur_date, amount=block_list_dict[member.name][i])
            TransactionData.objects.create(
                date=cur_date, amount=transaction_list[i])
            GasFeeData.objects.create(date=cur_date, amount=gas_fee_list[i])
    total_time = time.time() - starting_time
    return render(request, 'index/update.html', context={"time": total_time})


def get_end_date():
    transaction_data = [
        transaction for transaction in TransactionData.objects.all()]
    return transaction_data[-1].date


def collect_data_from_row(row, block_list_dict, transaction_list, gas_fee_list, start_date, address_name):
    cur_date = (datetime.datetime.strptime(row[0][:10], "%Y-%m-%d")).date()
    if cur_date >= start_date:
        date_delta = cur_date - start_date
        days_ind = date_delta.days
        block_list_dict[address_name][days_ind] = block_list_dict[address_name][days_ind] + 1
        transaction_list[days_ind] = transaction_list[days_ind] + int(row[1])
        gas_fee_list[days_ind] = gas_fee_list[days_ind] + float(row[2]) - 9.6
