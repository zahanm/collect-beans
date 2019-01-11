
import argparse
import json
from ofxclient import Institution
from ofxhome import OFXHome
from os import path
import shutil
import subprocess
import sys
from typing import Any, Dict

def run(CONFIG: Dict[str, Any]):
    parser = argparse.ArgumentParser(description="Download statements from banks")
    parser.add_argument('--days', type=int, default=10, help='How many days back should the statement go?')
    parser.add_argument('--out', '-o', required=True, help='Which folder to store the .ofx files in.')
    args = parser.parse_args(sys.argv[2:])

    session = None
    if any(acc['importer'] == 'OFX' for acc in CONFIG.values()):
        session = sign_in_to_op()

    # look up and download for each
    for name, account in CONFIG.items():
        if account['importer'] == 'OFX':
            ofx(args, session, name, account)
        elif account['importer'] == 'CSV':
            manual(args, name, account)
        else:
            assert False, 'Invalid importer: ' + repr(account)
        print()

def ofx(args, session, name, account):
    print('Account:', name)
    bank = OFXHome.lookup(account['OFX-id'])
    print('Bank:', bank.name)
    proceed = input('Should I download on this run? (y/n): ')
    if proceed[:1] != 'y':
        return
    (username, pw) = fetch_creds_from_op(session, account)
    client = Institution(bank.fid, bank.org, bank.url, username, pw)
    assert len(client.accounts()) == 1
    acc = client.accounts()[0]
    print('Fetching:', acc.long_description())
    statement = acc.download(days=args.days)
    fname = path.join(
        args.out,
        name + '_' + acc.number_masked()[-4:] + '.ofx')
    print('Writing:', fname)
    with open(fname, 'w') as f:
        shutil.copyfileobj(statement, f)

def sign_in_to_op():
    # check that op is installed, this will throw if not
    subprocess.run(['op', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # TODO check if you're signed in
    # sign in
    ret = subprocess.run(
        ['op', 'signin', '--output=raw'],
        check=True,
        stderr=sys.stderr,
        stdin=sys.stdin,
        stdout=subprocess.PIPE,
        text=True)
    session = ret.stdout
    return session

def fetch_creds_from_op(session, account):
    """fetch credentials from 1Password"""
    print('op get item', account['op-id'])
    # fetch the item
    ret = subprocess.run(
        ['op', 'get', 'item', account['op-id']],
        check=True,
        text=True,
        input=session,
        stdout=subprocess.PIPE)
    item = json.loads(ret.stdout)
    # parse out the username and password
    fields = item['details']['fields']
    assert any(f['designation'] == 'username' for f in fields)
    assert any(f['designation'] == 'password' for f in fields)
    for f in fields:
        if f['designation'] == 'username':
            username = f['value']
    for f in fields:
        if f['designation'] == 'password':
            pw = f['value']
    return (username, pw)

def manual(args, name, account):
    print('Account:', name)
    print('You need to download this', account['importer'], 'by hand')
    print('And put it in', args.out)
