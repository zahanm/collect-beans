
import argparse
from ofxclient import Institution
from ofxhome import OFXHome
from os import path
import shutil
import sys
from typing import Any, Dict

def run(CONFIG: Dict[str, Any]):
    parser = argparse.ArgumentParser(description="Download statements from banks")
    parser.add_argument('--days', type=int, default=5, help='How many days back should the statement go?')
    parser.add_argument('--out', '-o', required=True, help='Which folder to store the .ofx files in.')
    args = parser.parse_args(sys.argv[2:])

    # look up and download for each
    for name, account in CONFIG.items():
        if account['importer'] == 'OFX':
            ofx(args, name, account)
        elif account['importer'] == 'CSV':
            manual(args, name, account)
        else:
            assert False, 'Invalid importer: ' + repr(account)
        print()

def ofx(args, name, account):
    print('Account:', name)
    bank = OFXHome.lookup(account['OFX-id'])
    print('Bank:', bank.name)
    client = Institution(bank.fid, bank.org, bank.url, account['username'], account['pw'])
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

def manual(args, name, account):
    print('Account:', name)
    print('You need to download this', account['importer'], 'by hand')
    print('And put it in', args.out)
