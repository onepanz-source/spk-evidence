"""Research-only freshness receiver tests and T5DEF compatibility."""
import copy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from research.spk_v5_t5abc import t5abc
from research.spk_v5_t5ghi import t5ghi
from research.spk_v5_t5abc.tests.test_t5abc import FakeSchedulerEnv, module_import_at, workload

ROOT=Path(__file__).resolve().parents[3]
ISSUER=ROOT/'research/spk_v5_t5ghi/pe_challenge_issuer_v0.py'
FORK=ROOT/'research/spk_v5_t5ghi/live_challenge_fork_v0.py'

class TestT5GHI(unittest.TestCase):
    def test_custody(self):
        result=t5ghi.custody(ROOT)
        self.assertEqual(result['T5DEF_fork_sha256'],t5ghi.PARENT_FORK_SHA)
        self.assertEqual(result['frozen_BV_sha256'],t5abc.FROZEN_SHA)
    def test_reference_exact_hash(self):
        ref=t5abc.read_pinned(ROOT/'research/spk_v5_t5ghi/reference/t5def-pe-scope-issuer.json',
                             t5ghi.REF_SHA,'REFERENCE')
        self.assertEqual(ref['PE_scope_sign_issuances'],72)
        self.assertFalse(ref['promotion_allowed'])

    def make_receipt(self,index=0,sign=1):
        from research.spk_v5_t5ghi.receiver_authority_v0 import ReceiverVault
        from research.spk_v5_t5ghi.challenge_contract_v0 import challenge_digest
        v=ReceiverVault();ch=v.issue(index)
        issuance={'C_emission_id':'C-batch-3-tick-14','C_source':'C','tick':14,
             'source_channel':11 if sign==1 else 12,'sign':sign,'causal_parents':['r1'],
             'compute_batch':3}
        issuance['challenge_digest']=challenge_digest(ch,issuance)
        receipt={'receiver':'A','sender':'B','hop':2,'C_emission_id':issuance['C_emission_id'],
                'source_channel':issuance['source_channel'],'sign':sign,
                'challenge_digest':issuance['challenge_digest'],'receiver_authenticates_C':False}
        return v,ch,issuance,receipt

    def test_A_accepts_and_rejects_replay(self):
        v,ch,issue,receipt=self.make_receipt()
        self.assertTrue(v.verify(0,issue,receipt)['accepted'])
        with self.assertRaisesRegex(ValueError,'MISSING_OR_CONSUMED'):
            v.verify(0,issue,receipt)
        self.assertEqual(v.counts['accepted'],1)

    def test_wrong_case_then_real_accept(self):
        v,ch,issue,receipt=self.make_receipt()
        with self.assertRaisesRegex(ValueError,'MISSING_OR_CONSUMED'):
            v.verify(1,issue,receipt)
        self.assertTrue(v.verify(0,issue,receipt)['accepted'])

    def test_tamper_and_freshness(self):
        v,ch,issue,receipt=self.make_receipt()
        for forged in ('digest','sign','channel','sender','receiver','hop','emission'):
            a=copy.deepcopy(issue);b=copy.deepcopy(receipt)
            if forged=='digest':a['challenge_digest']='0'*64
            if forged=='sign':b['sign']=-1
            if forged=='channel':b['source_channel']=12
            if forged=='sender':b['sender']='C'
            if forged=='receiver':b['receiver']='X'
            if forged=='hop':b['hop']=1
            if forged=='emission':b['C_emission_id']='forged'
            with self.subTest(forged=forged):
                with self.assertRaises(ValueError):v.verify(0,a,b)
        self.assertTrue(v.verify(0,issue,receipt)['accepted'])

    def test_no_sign_expire(self):
        from research.spk_v5_t5ghi.receiver_authority_v0 import ReceiverVault
        v=ReceiverVault();v.issue(1);v.expire(1)
        self.assertEqual(v.counts['expired'],1)
        with self.assertRaises(ValueError):v.issue(1)

    def test_nonce_format_and_cross_nonce_replay(self):
        v,ch,issue,receipt=self.make_receipt()
        self.assertEqual(len(ch['nonce']),64)
        from research.spk_v5_t5ghi.challenge_contract_v0 import challenge_digest, PEIssuerRejected
        for changed in ({'case_index':0,'nonce':'nothex'}, {'case_index':True,'nonce':ch['nonce']},
                        {'case_index':0,'nonce':ch['nonce'],'fake':1}):
            with self.assertRaises(PEIssuerRejected):challenge_digest(changed,issue)
        ch2=v.issue(2)
        self.assertNotEqual(ch['nonce'],ch2['nonce'])
        with self.assertRaises(ValueError):v.verify(2,issue,receipt)

    def test_server_json_protocol(self):
        from research.spk_v5_t5ghi.receiver_authority_v0 import ReceiverVault
        v=ReceiverVault()
        self.assertTrue(v.handle({'op':'issue','case_index':0})['ok'])
        self.assertFalse(v.handle({'op':'issue','case_index':0})['ok'])
        self.assertFalse(v.handle({'op':'unknown'})['ok'])
        self.assertEqual(v.handle({'op':'expire','case_index':0})['expired'],True)

    def test_real_separate_A_process(self):
        a=t5ghi.AProcess()
        try:
            ch=a.issue(3)
            self.assertEqual(len(ch['nonce']),64)
            self.assertTrue(a.expire(3)['ok'])
            self.assertFalse(a.expire(3)['ok'])
            self.assertEqual(a.stats()['counts']['issued'],1)
        finally:a.close()

    def test_fork_synthetic_parity_and_binding(self):
        with FakeSchedulerEnv() as fake:
            old={name:sys.modules.get(name) for name in ['research.spk_v5_t5ghi.pe_challenge_issuer_v0']}
            issuer=module_import_at(ISSUER,'research.spk_v5_t5ghi.pe_challenge_issuer_v0')
            fork=module_import_at(FORK,'scratch_t5ghi_fork_test')
            try:
                for sign in (1,-1,None):
                    args=workload(sign)
                    token={'case_index':1,'nonce':'c'*64}
                    out=fork.execute_live_v0e(*args,bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30),receiver_challenge=token)
                    baseline=fake.fork.execute_live_v0e(*args,bv=fake.fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
                    self.assertEqual(t5abc.canon(t5ghi.strip_challenge(out)),t5abc.canon(baseline))
                    port=out['experimental_semantic_port']
                    self.assertEqual(len(port['issuances']),int(sign is not None))
                    if sign is not None:
                        issue=port['issuances'][0]
                        self.assertEqual(issue['challenge_digest'],issuer.challenge_digest(token,issue))
                        self.assertEqual(issue['challenge_digest'],port['receiver_A_sign_receipts'][0]['challenge_digest'])
            finally:
                sys.modules.pop('scratch_t5ghi_fork_test',None)
                for name,prev in old.items():
                    if prev is None:sys.modules.pop(name,None)
                    else:sys.modules[name]=prev

    def test_privileged_host_rebind_is_constructible(self):
        with FakeSchedulerEnv():
            old=sys.modules.get('research.spk_v5_t5ghi.pe_challenge_issuer_v0')
            issuer=module_import_at(ISSUER,'research.spk_v5_t5ghi.pe_challenge_issuer_v0')
            fork=module_import_at(FORK,'scratch_t5ghi_fork_test')
            original=fork.compute_and_issue
            saved=[];counter=[]
            try:
                ch1={'case_index':1,'nonce':'a'*64}
                def capture(node,*args):
                    result=original(node,*args)
                    if node.node_id=='C':saved.append(result)
                    return result
                fork.compute_and_issue=capture
                first=fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30),receiver_challenge=ch1)
                ch2={'case_index':2,'nonce':'b'*64};cached=iter(saved)
                def forged(node,*args):
                    if node.node_id!='C':return original(node,*args)
                    counter.append(True);res=next(cached)
                    return (*res[:3],replace(res[3],challenge_digest=issuer.challenge_digest(ch2,res[3].to_packet())))
                fork.compute_and_issue=forged
                second=fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30),receiver_challenge=ch2)
                self.assertEqual(len(counter),len(saved))
                self.assertEqual(t5abc.canon(t5ghi.strip_challenge(first)),t5abc.canon(t5ghi.strip_challenge(second)))
                self.assertNotEqual(first['experimental_semantic_port']['issuances'][0]['challenge_digest'],
                                    second['experimental_semantic_port']['issuances'][0]['challenge_digest'])
            finally:
                fork.compute_and_issue=original
                sys.modules.pop('scratch_t5ghi_fork_test',None)
                if old is None:sys.modules.pop('research.spk_v5_t5ghi.pe_challenge_issuer_v0',None)
                else:sys.modules['research.spk_v5_t5ghi.pe_challenge_issuer_v0']=old

if __name__=='__main__':unittest.main()
