from requests import get, post
from string import ascii_lowercase, ascii_uppercase, digits
from random import choice, choices


class TempMail:
    def __init__(self):
        for key, value in self._create_account().items():
            setattr(self, key, value)

    def __str__(self):
        return f'<id: {self.id} email: {self.email}>'

    def _set(self, email, id, token):
        self.token = token
        self.id = id
        self.email = email

    def _output(self):
        return self.email, self.id, self.token

    def _generate_email(self, domain: str = None):
        if not domain: domain = self._get_domains(True)
        return ''.join(choices(ascii_lowercase, k=10)) + '@' + domain

    def _generate_password(self, len: int = 8):
        return ''.join(choices(ascii_uppercase + ascii_lowercase + digits, k=len))

    def _get_domains(self, random: bool = False):
        resp = get('https://api.mail.tm/domains')
        domains = []
        for item in resp.json()['hydra:member']:
            if item['isActive']: domains.append(item['domain'])
        if random: return choice(domains)
        return domains

    def _create_account(self, email: str = None, password: str = None):
        if not email: email = self._generate_email()
        if not password: password = self._generate_password()
        resp = post(url='https://api.mail.tm/accounts', headers={'Content-Type': 'application/json'},
                    data='{"address":"' + email + '","password":"' + password + '"}')
        resp2 = post(url='https://api.mail.tm/token', headers={'Content-Type': 'application/json'},
                     data='{"address":"' + email + '","password":"' + password + '"}')
        return {'id': resp.json()['id'], 'email': resp.json()['address'], 'password': password,
                'token': resp2.json()['token']}

    def get_messages(self):
        resp = get('https://api.mail.tm/messages', headers={'Authorization': 'Bearer ' + self.token})
        return [Message(item, self.token) for item in resp.json()['hydra:member']]

    def get_mails(self):
        return self.get_messages()


class Message:
    def __init__(self, object: dict, token: str):
        self.id = object['id']
        self.from_addr = object['from']['address']
        self.from_name = object['from']['name']
        self.subject = object['subject']
        self.intro = object['intro']
        self.description = self.intro
        self.token = token

    def __str__(self):
        return '<' + self.subject + ' - ' + self.from_addr + '>'

    @property
    def text(self):
        resp = get('https://api.mail.tm/messages/' + self.id, headers={'Authorization': 'Bearer ' + self.token})
        return resp.json()['text']

    @property
    def html(self):
        resp = get('https://api.mail.tm/messages/' + self.id, headers={'Authorization': 'Bearer ' + self.token})
        return ''.join(resp.json()['html'])
