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
import asyncio
import aiohttp
from asgiref.sync import sync_to_async
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
                                 end_date, member.name + " Blocks", "Blocks", "block-member-download", member.address)
    except Member.DoesNotExist:
        raise Http404('Member does not exist')

    return render(request, 'index/graph_csv.html', context=context)


def transaction(request):
    transaction_amount_data = [
        transaction.amount for transaction in TransactionData.objects.all()]
    end_date = get_end_date()
    context = define_context(transaction_amount_data,
                             end_date, "Transactions", "Transactions", "transaction-download", "")

    return render(request, 'index/graph_csv.html', context=context)


def gas_fee(request):
    gas_amount_data = [
        gas.amount for gas in GasFeeData.objects.all()]
    end_date = get_end_date()
    context = define_context(gas_amount_data,
                             end_date, "Gas Fees", "Gas ($KLAY)", "gas-download", "")
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


def define_context(data, end_date, title, label, download, id):
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
    if id:
        context['download'] = reverse(download, args=[id])
    else:
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


def block_member_download(request, pk):
    try:
        member = Member.objects.get(pk=pk)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="' + \
            member.name + '_blocks.csv"'
        writer = csv.writer(response, csv.excel)
        response.write(u'\ufeff'.encode('utf8'))
        writer.writerow([smart_str(u"Date"), smart_str(u"Blocks")])
        for blocks in BlockData.objects.filter(member=member):
            writer.writerow([smart_str(blocks.date), smart_str(blocks.amount)])
        return response
    except Member.DoesNotExist:
        raise Http404('Member does not exist')


async def update(request):
    starting_time = time.time()
    start_date = await get_end_date_async()
    start_date = start_date+datetime.timedelta(days=1)
    end_date = datetime.date.today()-datetime.timedelta(days=1)
    if start_date <= end_date:
        start_month = datetime.datetime(start_date.year, start_date.month, 1)
        end_month = datetime.datetime(end_date.year, end_date.month, 1)
        date_delta = end_date - start_date
        num_days = date_delta.days + 1
        block_list_dict = {}
        members = await get_all_members()
        for member in members:
            block_list_dict[member.name] = np.zeros(num_days, dtype=np.uint32)
        transaction_list = np.zeros(num_days, dtype=np.uint64)
        gas_fee_list = np.zeros(num_days)
        request_link1 = "https://api-cypress-v2.scope.klaytn.com/v2/accounts/"
        request_link2 = "/blocks/download?date="
        async with aiohttp.ClientSession() as session:
            tasks = []
            while start_month <= end_month:
                for member in members:
                    if not member.active:
                        continue
                    url = request_link1 + member.address + request_link2 + \
                        datetime.datetime.strftime(start_month, "%Y-%m")
                    task = asyncio.ensure_future(download(
                        session, url, block_list_dict, transaction_list, gas_fee_list, start_date, member))
                    tasks.append(task)
                start_month = start_month + relativedelta(months=1)
            await asyncio.gather(*tasks, return_exceptions=False)
        for i in range(num_days):
            cur_date = start_date+datetime.timedelta(days=i)
            for member in members:
                await create_block_data(member, cur_date, block_list_dict[member.name][i])
            await create_transaction_data(cur_date, transaction_list[i])
            await create_gas_fee_data(cur_date, gas_fee_list[i])
    total_time = time.time() - starting_time
    return render(request, 'index/update.html', context={"time": total_time})


def get_end_date():
    transaction_data = [
        transaction for transaction in TransactionData.objects.all()]
    return transaction_data[-1].date


@sync_to_async
def get_end_date_async():
    return get_end_date()


def collect_data_from_row(row, block_list_dict, transaction_list, gas_fee_list, start_date, address_name):
    cur_date = (datetime.datetime.strptime(row[0][:10], "%Y-%m-%d")).date()
    if cur_date >= start_date:
        date_delta = cur_date - start_date
        days_ind = date_delta.days
        block_list_dict[address_name][days_ind] = block_list_dict[address_name][days_ind] + 1
        transaction_list[days_ind] = transaction_list[days_ind] + int(row[1])
        gas_fee_list[days_ind] = gas_fee_list[days_ind] + float(row[2]) - 9.6


@sync_to_async
def get_all_members():
    return list(Member.objects.all())


@sync_to_async
def create_block_data(member, date, amount):
    BlockData.objects.create(member=member, date=date, amount=amount)


@sync_to_async
def create_transaction_data(date, amount):
    TransactionData.objects.create(date=date, amount=amount)


@sync_to_async
def create_gas_fee_data(date, amount):
    GasFeeData.objects.create(date=date, amount=amount)


async def download(session, url, block_list_dict, transaction_list, gas_fee_list, start_date, member):
    head = {"referer": "https://scope.klaytn.com/"}
    async with session.get(url, headers=head) as response:
        data = await response.text()
        if data and data[0] != "<":
            df = pd.read_csv(StringIO(data),
                             usecols=[1, 2, 3])
            df.apply(lambda row: collect_data_from_row(
                row, block_list_dict, transaction_list, gas_fee_list, start_date, member.name), axis=1)
