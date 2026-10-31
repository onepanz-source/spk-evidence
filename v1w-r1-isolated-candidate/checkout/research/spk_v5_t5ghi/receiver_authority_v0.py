"""Receiver A owns random challenge issuance and one-use ledger in a SEPARATE Python process.

This is a research process boundary, NOT protection against a privileged host.
The nonce is visible to the fork's host: possession proves freshness, not C origin.
"""
from __future__ import annotations
import json
import secrets
import sys
from .challenge_contract_v0 import challenge_digest, PEIssuerRejected

class Rejected(ValueError): pass

def require(test,code):
    if not test:raise Rejected(code)

class ReceiverVault:
    def __init__(self):
        self.outstanding={};self.finished=set();self.counts={'issued':0,'accepted':0,'expired':0,'rejected':0}

    def issue(self,case_index):
        require(type(case_index) is int and case_index>=0,'CASE_ID_INVALID')
        require(case_index not in self.outstanding and case_index not in self.finished,'ISSUE_REPLAY')
        token=secrets.token_hex(32)
        self.outstanding[case_index]=token
        self.counts['issued']+=1
        return {'case_index':case_index,'nonce':token}

    def reject(self,reason):
        self.counts['rejected']+=1
        raise Rejected(reason)

    def verify(self,case_index,issuance,receipt):
        if type(case_index) is not int or case_index not in self.outstanding:
            self.reject('MISSING_OR_CONSUMED_CHALLENGE')
        if type(issuance) is not dict or type(receipt) is not dict:
            self.reject('INVALID_RECEIPT_SHAPE')
        nonce=self.outstanding[case_index]
        challenge={'case_index':case_index,'nonce':nonce}
        try:expected=challenge_digest(challenge,issuance)
        except (PEIssuerRejected,ValueError,KeyError,TypeError):self.reject('CHALLENGE_DIGEST_INPUT_INVALID')
        if issuance.get('challenge_digest')!=expected or receipt.get('challenge_digest')!=expected:
            self.reject('CHALLENGE_DIGEST_MISMATCH')
        if (receipt.get('C_emission_id')!=issuance.get('C_emission_id') or
            receipt.get('sign')!=issuance.get('sign') or
            receipt.get('source_channel')!=issuance.get('source_channel') or
            receipt.get('receiver')!='A' or receipt.get('sender')!='B' or receipt.get('hop')!=2 or
            receipt.get('receiver_authenticates_C') is not False):
            self.reject('RECEIVER_CUSTODY_MISMATCH')
        if issuance.get('C_source')!='C' or issuance.get('sign') not in (-1,1) or \
            issuance.get('source_channel')!=(11 if issuance.get('sign')==1 else 12):
            self.reject('SEMANTIC_SIGN_INVALID')
        self.finished.add(case_index)
        del self.outstanding[case_index]
        self.counts['accepted']+=1
        return {'accepted':True,'research_only':True,'native_authenticated':False}

    def expire(self,case_index):
        require(type(case_index) is int and case_index in self.outstanding,'MISSING_OR_CONSUMED_CHALLENGE')
        del self.outstanding[case_index];self.finished.add(case_index);self.counts['expired']+=1
        return {'expired':True}

    def handle(self,request):
        try:
            require(type(request) is dict,'REQUEST_SHAPE')
            op=request.get('op')
            if op=='issue':return {'ok':True,'challenge':self.issue(request.get('case_index'))}
            if op=='verify':return {'ok':True,**self.verify(request.get('case_index'),request.get('issuance'),request.get('receipt'))}
            if op=='expire':return {'ok':True,**self.expire(request.get('case_index'))}
            if op=='stats':return {'ok':True,'counts':dict(self.counts),'outstanding':len(self.outstanding)}
            self.reject('OP_UNSUPPORTED')
        except (Rejected,ValueError,TypeError,KeyError) as exc:
            return {'ok':False,'reason':str(exc)}

def main():
    authority=ReceiverVault()
    for line in sys.stdin:
        try:
            request=json.loads(line)
            answer=authority.handle(request)
        except Exception:
            answer={'ok':False,'reason':'PROTOCOL_INVALID'}
        sys.stdout.write(json.dumps(answer,sort_keys=True,separators=(',',':'))+'\n')
        sys.stdout.flush()

if __name__=='__main__':main()
