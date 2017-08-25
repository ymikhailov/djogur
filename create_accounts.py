from main.models import *

def load_accounts():
    accounts = []
    with open('accounts.txt') as fp:
        for line in fp:
            ln = line.split()
            accounts = accounts + [[ln[0], ln[2], ln[1], ln[4], ln[6]]]

    return accounts

def create_account(account):
    u = User()
    u.username = account[3]
    u.set_password(account[4])
    u.save()

    p = Profile()
    p.user = u
    p.first_name = account[1]
    p.last_name = account[2]
    p.league = account[0]
    p.save()

def run():
    accounts = load_accounts()
    for account in accounts:
        create_account(account)
