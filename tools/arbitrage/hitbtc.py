#!/usr/bin/env python
import sys
import urllib2
from time import sleep
import json

from arbitrator import BlinkTradeArbitrator

import datetime
import hmac
import hashlib
import ConfigParser
from ws4py.exc import HandshakeError


HITBTC_API_KEY = 'XXXX'
HITBTC_API_SECRET = 'YYYY'

def send_order(sender, order):
  nonce = datetime.datetime.now().strftime('%s')
  message = 'sendorder' + str(HITBTC_API_KEY) + str(nonce)
  signature = hmac.new(HITBTC_API_SECRET, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

  post_params = {
    'key': HITBTC_API_KEY,
    'sign': signature,
    'pair': 'btc_brl',
    'volume': float(order['OrderQty']/1.e8),
    'price': float( order['Price'] / 1.e8)
  }

  if order['Side'] == '1':
    post_params['type'] = 'buy'
  elif order['Side'] == '2':
    post_params['type'] = 'sell'

  print datetime.datetime.now(), 'POST https://api.hitbtc.com/v1/tapi/' + message, str(post_params)

def main():
  candidates = ['arbitrage.ini', 'hitbtc.ini' ]
  if len(sys.argv) > 1:
    candidates.append(sys.argv[1])


  config = ConfigParser.SafeConfigParser({
    'websocket_url': 'wss://127.0.0.1/trade/',
    'username': '',
    'password': '',
    'buy_fee': 0,
    'sell_fee': 0,
    'api_key': 'KEY',
    'api_secret': 'SECRET'
  })
  config.read( candidates )

  websocket_url = config.get('hitbtc', 'websocket_url')
  username      = config.get('hitbtc', 'username')
  password      = config.get('hitbtc', 'password')
  buy_fee       = int(config.get('hitbtc', 'buy_fee'))
  sell_fee      = int(config.get('hitbtc', 'sell_fee'))
  api_key       = config.get('hitbtc', 'api_key')
  api_secret    = config.get('hitbtc', 'api_secret')


  arbitrator = BlinkTradeArbitrator(username,password,websocket_url, 'BTCUSD')
  arbitrator.connect()

  arbitrator.signal_order.connect(send_order)

  while True:
    try:
      sleep(1)
      if arbitrator.is_connected():
        arbitrator.send_testRequest()
      else:
        try:
          arbitrator.reconnect()
        except HandshakeError,e:
          continue

      try:
        raw_data = urllib2.urlopen('https://api.hitbtc.com/api/1/public/BTCUSD/orderbook?format_price=number&format_amount=number').read()
      except Exception:
        print 'ERROR RETRIEVING ORDER BOOK'
        continue


      bids_asks = []
      try:
        bids_asks = json.loads(raw_data)
      except  Exception :
        pass

      if bids_asks:
        bid_list = [ [  int(float(o[0]) * 1e8 * (1. + buy_fee) ) , int( float(o[1]) * 1e8) ] for o in bids_asks['bids'] ]
        ask_list = [ [  int(float(o[0]) * 1e8 * (1. + sell_fee) ) , int( float(o[1]) * 1e8) ] for o in bids_asks['asks'] ]
        arbitrator.process_ask_list(ask_list)
        arbitrator.process_bid_list(bid_list)
    except urllib2.URLError as e:
      print datetime.datetime.now(), e

    except KeyboardInterrupt:
      arbitrator.cancel_all_orders()
      print 'wait....'
      sleep(5)
      arbitrator.close()
      break

main()

