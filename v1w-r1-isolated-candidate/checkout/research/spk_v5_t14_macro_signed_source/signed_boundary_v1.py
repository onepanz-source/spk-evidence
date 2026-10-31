"""T14 research: detached Ed25519 feedback custody at a C tick.

The signer is NOT included; a test harness may supply laboratory signatures.
Production with no separately controlled signer fails closed. Source semantic
truth is not established by a signature over host-authored goals/observations.
The unchanged SPK originals are never issued learning/P authority.
"""
from __future__ import annotations
import base64, hashlib, json, os, sqlite3, subprocess, tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, digest, pack
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import OriginalAccessGatedV1

SCHEMA='spk-v5-t14-detached-A-feedback/v1'
KEY_TABLE="""CREATE TABLE t14_source_key (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  issuer TEXT NOT NULL CHECK(issuer='A-EXTERNAL'),
  public_der_sha256 TEXT NOT NULL CHECK(length(public_der_sha256)=64)
)"""
ATTEST_TABLE="""CREATE TABLE t14_attestation (
  episode_id INTEGER PRIMARY KEY,
  a_event_id INTEGER NOT NULL UNIQUE,
  a_event_digest TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  signature_b64 TEXT NOT NULL,
  pub_sha256 TEXT NOT NULL,
  UNIQUE(episode_id,a_event_digest)
)"""
LINK_TABLE="""CREATE TABLE t14_grant_link (
  grant_id INTEGER PRIMARY KEY,
  episode_id INTEGER NOT NULL UNIQUE,
  a_event_id INTEGER NOT NULL,
  a_event_digest TEXT NOT NULL,
  attestation_sha256 TEXT NOT NULL,
  signature_sha256 TEXT NOT NULL
)"""
LINK_TRIGGER="""CREATE TRIGGER spk_t14_signed_source_grant
AFTER INSERT ON reference_provider_receipt BEGIN
 INSERT INTO t14_grant_link
 SELECT NEW.grant_id, ep.id, att.a_event_id, att.a_event_digest,
        spk_t14_payload_sha(att.payload_json),spk_t14_signature_sha(att.signature_b64)
 FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
 JOIN t14_attestation att ON att.episode_id=ep.id
 WHERE g.id=NEW.grant_id AND g.cue=NEW.cue AND g.expected_version=NEW.expected_version
   AND spk_t14_verify(att.episode_id,att.payload_json,att.signature_b64)=1;
 SELECT RAISE(ABORT,'T14_SIGNED_A_SOURCE_REQUIRED') WHERE NOT EXISTS
   (SELECT 1 FROM t14_grant_link WHERE grant_id=NEW.grant_id);
END"""


def openssl(*args, input_bytes=None):
    p=subprocess.run(['openssl',*args],input=input_bytes,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,timeout=10,check=False)
    ensure(p.returncode==0,'T14_OPENSSL_FAILURE:'+p.stderr.decode('utf-8','replace')[:160])
    return p.stdout


def public_der_from_pem(pub:bytes)->bytes:
    with tempfile.TemporaryDirectory(prefix='spk-t14-pub-') as td:
        path=Path(td)/'public.pem';path.write_bytes(pub)
        return openssl('pkey','-pubin','-in',str(path),'-pubout','-outform','DER')


def verify_detached(pub:bytes, message:bytes, signature:bytes)->bool:
    if len(signature)!=64:return False
    with tempfile.TemporaryDirectory(prefix='spk-t14-verify-') as td:
        key=Path(td)/'public.pem';msg=Path(td)/'msg.bin';sig=Path(td)/'sig.bin'
        key.write_bytes(pub);msg.write_bytes(message);sig.write_bytes(signature)
        result=subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(key),
                  '-rawin','-in',str(msg),'-sigfile',str(sig)],
                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        return result.returncode==0


def sign_detached_for_lab(private_key:Path, payload:bytes):
    """Laboratory only: runtime never imports or calls this function."""
    with tempfile.TemporaryDirectory(prefix='spk-t14-sign-lab-') as td:
        msg=Path(td)/'msg';msg.write_bytes(payload)
        return openssl('pkeyutl','-sign','-inkey',str(private_key),'-rawin','-in',str(msg))


class SignedSourceGatedV1(OriginalAccessGatedV1):
    def __init__(self,path,*,public_key_pem:bytes,root=None,learn=True,max_inflight=3,
                 create=True,test_witness=None,test_only=False):
        ensure(isinstance(public_key_pem,bytes) and b'BEGIN PUBLIC KEY' in public_key_pem,
               'T14_PUBLIC_KEY_REQUIRED')
        self.external_public_key=public_key_pem
        self.external_key_digest=hashlib.sha256(public_der_from_pem(public_key_pem)).hexdigest()
        super().__init__(path,root=root,learn=learn,max_inflight=max_inflight,
                         create=create,test_witness=test_witness,test_only=test_only)
        self.db.create_function('spk_t14_payload_sha',1,lambda x:hashlib.sha256(x.encode()).hexdigest())
        self.db.create_function('spk_t14_signature_sha',1,lambda x:hashlib.sha256(base64.b64decode(x,validate=True)).hexdigest())
        self.db.create_function('spk_t14_verify',3,self._verify_for_sql)
        if create:
            self.db.execute(KEY_TABLE)
            self.db.execute('INSERT INTO t14_source_key VALUES(1,?,?)',('A-EXTERNAL',self.external_key_digest))
            self.db.execute(ATTEST_TABLE)
            self.db.execute(LINK_TABLE)
            self.db.execute(LINK_TRIGGER)
        self.audit_signed_source()

    def reopen(self):
        self.close()
        self.__init__(self.path,public_key_pem=self.external_public_key,root=self.source_root,
                      learn=self.learn,max_inflight=self.max_inflight,create=False,
                      test_witness=self.test_witness,test_only=self.test_only)

    def expected_message(self,episode_id:int)->bytes:
        ep=self.db.execute('SELECT * FROM episode WHERE id=?',(episode_id,)).fetchone()
        ensure(ep is not None,'T14_EPISODE_MISSING')
        a=self.db.execute("SELECT * FROM event WHERE episode_id=? AND kind='PE_A' AND status='DONE'",
                          (episode_id,)).fetchall()
        ensure(len(a)==1,'T14_NO_COMPLETED_A_PE_EVENT')
        # Bind exactly the A response, its PE provenance and the policy-version seen by C.
        ev=a[0]
        from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import pe_step
        x=pe_step('A',ep['choice'],ep['goal'],12,[3 if ep['choice']==11 else 4])
        ensure(x['emits']==[21 if ep['choice']==ep['goal'] else 22,7], 'T14_A_SEMANTICS_DRIFT')
        payload={'schema':SCHEMA,'issuer':'A-EXTERNAL','episode_id':episode_id,
                'cue':ep['cue'],'decision_choice':ep['choice'],'goal':ep['goal'],
                'expected_P_version':ep['version'],'A_event_id':ev['id'],
                'A_event_digest':ev['digest'],'A_PE_digest':digest(x),
                'verdict':'IMPROVED' if ep['choice']==ep['goal'] else 'WORSENED',
                'nonce':ev['digest']}
        return pack(payload).encode('utf-8')

    def ingest(self,episode_id:int,message:bytes,signature:bytes):
        ensure(type(episode_id) is int and type(message) is bytes and type(signature) is bytes,
               'T14_PACKET_TYPES')
        ep=self.db.execute('SELECT status FROM episode WHERE id=?',(episode_id,)).fetchone()
        ensure(ep is not None and ep['status']=='RUNNING','T14_LATE_SETTLED_ATTESTATION')
        ensure(not self.db.execute("SELECT 1 FROM event WHERE episode_id=? AND kind='SEM_B_C' AND status='DONE'",(episode_id,)).fetchone(),
               'T14_RECEIPT_AFTER_C_COMMIT')
        expected=self.expected_message(episode_id)
        ensure(message==expected,'T14_OBSERVATION_OR_LINEAGE_MISMATCH')
        ensure(verify_detached(self.external_public_key,message,signature),'T14_BAD_SIGNATURE')
        data=json.loads(message)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            ensure(self.db.execute('SELECT 1 FROM t14_attestation WHERE episode_id=?',(episode_id,)).fetchone() is None,
                   'T14_DUPLICATE_RECEIPT')
            self.db.execute('INSERT INTO t14_attestation VALUES(?,?,?,?,?,?)',
                (episode_id,data['A_event_id'],data['A_event_digest'],message.decode('utf-8'),
                 base64.b64encode(signature).decode('ascii'),self.external_key_digest))
            self._log('T14_EXTERNAL_ATTESTATION',{'episode_id':episode_id,
                         'message_sha256':hashlib.sha256(message).hexdigest(),
                         'signature_sha256':hashlib.sha256(signature).hexdigest()})
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def _verify_for_sql(self,episode_id,payload_json,signature_b64):
        try:
            expected=self.expected_message(episode_id)
            if payload_json.encode('utf-8')!=expected:return 0
            row=self.db.execute('SELECT pub_sha256 FROM t14_attestation WHERE episode_id=?',(episode_id,)).fetchone()
            if row is None or row[0]!=self.external_key_digest:return 0
            return int(verify_detached(self.external_public_key,expected,
                           base64.b64decode(signature_b64,validate=True)))
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError):return 0

    def _authorize(self,cue,old_choice,version,budget,new_choice,new_version,new_budget):
        # CRITICAL: deny before running the costly ORIGINAL A1d memory chain.
        matches=self.db.execute('''SELECT ep.id FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
            WHERE g.cue=? AND g.expected_version=? AND ep.choice=? AND ep.status='RUNNING' ''',
            (cue,version,old_choice)).fetchall()
        if len(matches)!=1:return 0
        att=self.db.execute('SELECT * FROM t14_attestation WHERE episode_id=?',(matches[0][0],)).fetchone()
        if att is None or not self._verify_for_sql(matches[0][0],att['payload_json'],att['signature_b64']):return 0
        return super()._authorize(cue,old_choice,version,budget,new_choice,new_version,new_budget)

    def audit_signed_source(self):
        for typ,name,expected in [('table','t14_source_key',KEY_TABLE),
                    ('table','t14_attestation',ATTEST_TABLE),('table','t14_grant_link',LINK_TABLE),
                    ('trigger','spk_t14_signed_source_grant',LINK_TRIGGER)]:
            r=self.db.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?',(typ,name)).fetchone()
            ensure(r is not None and r[0]==expected,'T14_SCHEMA_OR_TRIGGER_DRIFT:'+name)
        key=self.db.execute('SELECT * FROM t14_source_key WHERE singleton=1').fetchone()
        ensure(key is not None and key['issuer']=='A-EXTERNAL' and key['public_der_sha256']==self.external_key_digest,
               'T14_PUBLIC_KEY_PIN_DRIFT')
        for row in self.db.execute('SELECT * FROM t14_attestation'):
            ensure(row['pub_sha256']==self.external_key_digest and
                   self._verify_for_sql(row['episode_id'],row['payload_json'],row['signature_b64']),
                   'T14_ATTESTATION_CUSTODY_DRIFT')
        grants=[dict(r) for r in self.db.execute('SELECT * FROM p_grant ORDER BY id')]
        links=[dict(r) for r in self.db.execute('SELECT * FROM t14_grant_link ORDER BY grant_id')]
        ensure(len(grants)==len(links),'T14_ATTESTED_GRANT_COUNT_DRIFT')
        for g,l in zip(grants,links):
            ep=self.db.execute('SELECT * FROM episode WHERE id=?',(g['episode_id'],)).fetchone()
            att=self.db.execute('SELECT * FROM t14_attestation WHERE episode_id=?',(g['episode_id'],)).fetchone()
            ensure(ep is not None and att is not None and (g['id'],g['episode_id'])==(l['grant_id'],l['episode_id'])
                   and l['a_event_id']==att['a_event_id'] and l['a_event_digest']==att['a_event_digest']
                   and l['attestation_sha256']==hashlib.sha256(att['payload_json'].encode()).hexdigest()
                   and l['signature_sha256']==hashlib.sha256(base64.b64decode(att['signature_b64'])).hexdigest()
                   and self._verify_for_sql(ep['id'],att['payload_json'],att['signature_b64']),
                   'T14_ATTESTED_CREDIT_DRIFT')
        return {'signed_receipts_observed':self.db.execute('SELECT COUNT(*) FROM t14_attestation').fetchone()[0],
                'signed_P_grants':len(links),'original_learning_P_grants':0,
                'original_source_sensor_authenticated':False,
                'cryptographic_key_control_tested':True,
                'host_runtime_trust_boundary_unproven':True,
                'source_private_key_stored_in_runtime':False}
