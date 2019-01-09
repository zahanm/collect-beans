
import argparse
from ofxclient import Institution
from ofxhome import OFXHome
from os import path
import shutil
import sys
import yaml

def run():
  parser = argparse.ArgumentParser(description="Download statements from banks")
  parser.add_argument('--days', type=int, default=5, help='How many days back should the statement go?')
  parser.add_argument('--out', '-o', required=True, help='Which folder to store the .ofx files in.')
  args = parser.parse_args(sys.argv[2:])

  # load accounts config
  fname = path.join(path.dirname(__file__), 'CONFIG.yaml')
  with open(fname) as f:
      CONFIG = yaml.load(f)

  # look up and download for each
  for name, importer in CONFIG.items():
      print('Importer:', name)
      bank = OFXHome.lookup(importer['OFX-ID'])
      print('Bank:', bank.name)
      client = Institution(bank.fid, bank.org, bank.url, importer['username'], importer['pw'])
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
