import dns.resolver
import hashlib
import httplib
import irc.client
import logging
import random
import smtplib
import socket
import string
import urllib

logger = logging.getLogger(__name__)

HOSTNAME = 'localhost'
IPADDR = '127.0.0.1'

###############################################################################
# (Utility)
###############################################################################

def _util_gen_randstr(min=6, max=6, set=string.letters + string.digits):
    n = random.choice(range(min, max + 1))
    s = ''.join(random.choice(set) for i in range(n))
    return s

###############################################################################
# HTTP/S
###############################################################################

def _util_ht_expect_fakenet(nm, meth, uri, hostname, port=None, secure=False,
        data=None, hdrs={}):
    c = None

    if secure:
        if port is None:
            port = 443
        c = httplib.HTTPSConnection(hostname, port)
    else:
        if port is None:
            port = 80
        c = httplib.HTTPConnection(hostname, port)

    c.request('GET', '/', data, hdrs)
    r = c.getresponse()
    logger.info('{0}: {1} {2}'.format(nm, str(r.status), r.reason))
    assert 200 == r.status
    assert 'OK' == r.reason
    d = r.read()
    assert 'FakeNet' in d

def test_http_get_slash():
    nm = test_http_get_slash.__name__
    _util_ht_expect_fakenet(nm, 'GET', '/', HOSTNAME, secure=False)

def test_http_post_slash():
    nm = test_http_post_slash.__name__
    d = urllib.urlencode({'a': 123, 'b': 'asdf'})
    _util_ht_expect_fakenet(nm, 'POST', '/', HOSTNAME, secure=False, data=d)

def test_https_get_slash():
    nm = test_https_get_slash.__name__
    _util_ht_expect_fakenet(nm, 'GET', '/', HOSTNAME, secure=True)

def test_https_post_slash():
    nm = test_http_post_slash.__name__
    d = urllib.urlencode({'a': 123, 'b': 'asdf'})
    _util_ht_expect_fakenet(nm, 'POST', '/', HOSTNAME, secure=True, data=d)

def test_http_get_random():
    nm = test_http_get_random.__name__
    u = _util_gen_randstr(3, 8)
    logger.info('{0}: requesting random URI {1}'.format(nm, u))
    _util_ht_expect_fakenet(nm, 'GET', u, HOSTNAME, secure=False)

def test_https_get_random():
    nm = test_https_get_random.__name__
    u = _util_gen_randstr(3, 8)
    logger.info('{0}: requesting random URI {1}'.format(nm, u))
    _util_ht_expect_fakenet(nm, 'GET', u, HOSTNAME, secure=True)

def test_http_get_long():
    nm = test_http_get_long.__name__
    u = _util_gen_randstr(4096, 4096)
    _util_ht_expect_fakenet(nm, 'GET', u, HOSTNAME, secure=False)

def test_https_get_long():
    nm = test_https_get_long.__name__
    u = _util_gen_randstr(4096, 4096)
    _util_ht_expect_fakenet(nm, 'GET', u, HOSTNAME, secure=False)

###############################################################################
# DNS
###############################################################################

def _util_ns_expect_identical(nm, type_, dom1, dom2):
    r = dns.resolver.Resolver()
    r.nameservers = [IPADDR]
    s1 = set([str(answer) for answer in r.query(dom1, type_)])
    s2 = set([str(answer) for answer in r.query(dom2, type_)])
    assert len(s1.symmetric_difference(s2)) == 0

def test_ns_a_expect_identical_replies():
    nm = test_ns_a_expect_identical_replies.__name__
    _util_ns_expect_identical(nm, 'A', 'www.google.com', 'www.yahoo.com')

def test_ns_mx_expect_identical_replies():
    nm = test_ns_mx_expect_identical_replies.__name__
    _util_ns_expect_identical(nm, 'MX', 'www.google.com', 'www.yahoo.com')

def test_ns_txt_expect_identical_replies():
    nm = test_ns_txt_expect_identical_replies.__name__
    _util_ns_expect_identical(nm, 'TXT', 'www.google.com', 'www.yahoo.com')

###############################################################################
# SMTP
###############################################################################

def _util_smtp(nm, hostname, port, secure=False, starttls=False):
    c = None
    if secure:
        c = smtplib.SMTP_SSL(hostname, port)
    else:
        c = smtplib.SMTP(hostname, port)

    c.ehlo('test.evil.com')
    if starttls:
        c.starttls()

    data = 'hai hai\r\n'
    c.sendmail('sender@example.com', 'recipient@example.com', data)

    c.quit()

def test_smtp():
    nm = test_smtp.__name__
    _util_smtp(nm, HOSTNAME, 25)

###############################################################################
# IRC
###############################################################################

def _util_irc(nm, hostname, port, nick, privmsgs):
    c = irc.client.Reactor()
    s = c.server()
    s.connect(hostname, port, nick)
    for (nick, msg) in privmsgs:
        s.privmsg(nick, msg)
    s.close()

def test_irc():
    nm = test_irc.__name__
    privmsgs = [
        ['#evil_bartenders', 'Black Market'],
        ['inspector_clouseau', "I'm looking for a safe house."],
    ]
    _util_irc(nm, HOSTNAME, 6667, 'dr_evil', privmsgs)


###############################################################################
# 1337 (raw TCP)
###############################################################################

def _util_raw_expect_same_back(nm, ipaddr, port, data, secure=False):
    if secure:
        raise Exception('secure raw socket util not yet implemented')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect( (ipaddr, port) )
    s.send(data)
    r = s.recv(1024)
    assert r == data

def test_1337():
    nm = test_1337.__name__
    _util_raw_expect_same_back(nm, IPADDR, 1337, 'hai hai\r\n')
