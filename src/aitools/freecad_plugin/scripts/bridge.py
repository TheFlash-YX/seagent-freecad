"""JSON-lines stdio management bridge. Upstream business payloads are not rewritten."""
import argparse
import json
import os
from pathlib import Path
import queue
import re
import shlex
import subprocess
import sys
import threading
import uuid
import manage

WRITE=threading.Lock()
SUPPORTED={'2024-11-05','2025-03-26','2025-06-18','2025-11-25'}


def send(value):
    with WRITE:
        sys.stdout.write(json.dumps(value,ensure_ascii=False)+'\n');sys.stdout.flush()


def result(id,v):send({'jsonrpc':'2.0','id':id,'result':v})
def error(id,code,message):send({'jsonrpc':'2.0','id':id,'error':{'code':code,'message':message}})
def text(value,failed=False):return {'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'isError':failed}


class Upstream:
    def __init__(self,data,project,protocol):
        c=manage.read(data/'machine.json');ready=manage.validate_runtime(data)
        # POSIX shlex is upstream's actual parser even on Windows.
        argv=[str(Path(x).as_posix()) if i==0 else x for i,x in enumerate(c['freecadcmd'])]
        cmd=[ready['mcp'],'--host','127.0.0.1','--freecadcmd',shlex.join(argv)]
        self.proc=subprocess.Popen(cmd,cwd=project,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                   stderr=sys.stderr,text=True,encoding='utf-8',bufsize=1)
        self.waiters={};self.lock=threading.Lock();self.closed=False
        threading.Thread(target=self.reader,daemon=True).start()
        init=self.call({'method':'initialize','params':{'protocolVersion':protocol,'capabilities':{},'clientInfo':{'name':'seagent-management-bridge','version':'0.2.0'}}})
        if 'error' in init:raise RuntimeError('上游初始化失败')
        self.notify({'method':'notifications/initialized'})
    def notify(self,v):
        with self.lock:
            if self.proc.poll() is not None:raise RuntimeError('上游已退出')
            self.proc.stdin.write(json.dumps(dict(jsonrpc='2.0',**v),ensure_ascii=False)+'\n');self.proc.stdin.flush()
    def call(self,v,request_id=None):
        rid=request_id or ('bridge-'+uuid.uuid4().hex);q=queue.Queue()
        with self.lock:self.waiters[rid]=q
        self.notify(dict(v,id=rid))
        r=q.get()
        if r is None:raise RuntimeError('上游连接中断；请求结果未知，不自动重试')
        return r
    def reader(self):
        try:
            for line in self.proc.stdout:
                v=json.loads(line)
                if 'id' in v and ('result'in v or 'error'in v):
                    with self.lock:q=self.waiters.pop(v['id'],None)
                    if q:q.put(v)
                elif 'id' not in v:send(v)  # Preserve progress/log notifications.
                else:
                    # Capabilities advertised to upstream are empty; server requests unsupported.
                    self.notify({'id':v['id'],'error':{'code':-32601,'message':'Client capability not advertised'}})
        finally:
            with self.lock:
                self.closed=True
                for q in self.waiters.values():q.put(None)
                self.waiters.clear()
    def close(self):
        # Closing stdio does not kill FreeCAD or a headless helper. Pending ledger remains.
        try:self.proc.stdin.close()
        except OSError:pass


class Bridge:
    def __init__(self,data):
        self.data=data;self.snapshot=None;self.up=None;self.protocol='2025-11-25'
        self.busy=threading.Lock();self.ids={}
        self.tools=manage.read(manage.PACKAGE/'references/tools.schema.json')['tools']
    def handshake(self,args):
        receipt=manage.read(self.data/'prepare.json')
        if not args.get('marker') or args['marker']!=receipt.get('marker'):
            raise RuntimeError('握手必须使用当前聊天exec prepare返回的标记，不接受猜测路径')
        b={k:receipt[k] for k in ('schema','project','generation')}
        if self.snapshot is not None and self.snapshot!=b:
            raise RuntimeError('旧连接不能重新绑定新项目；请建立新MCP连接')
        with manage.locked(self.data):
            if manage.read(self.data/'binding.json')!=b:raise RuntimeError('prepare回执已过期')
            manage.guard(self.data,b)
            owner=manage.read(self.data/'connection.json') if (self.data/'connection.json').exists() else None
            if owner and owner.get('generation')==b['generation'] and owner['pid']!=os.getpid() and manage.identity(owner['pid'])==owner['identity']:
                raise RuntimeError('本项目已由另一MCP连接控制，请停止旧聊天连接；不并发调度')
            if receipt.get('consumed_by') not in (None,os.getpid()):raise RuntimeError('prepare标记已被另一连接消费；单聊天单连接')
            manage.write(self.data/'connection.json',dict(pid=os.getpid(),identity=manage.identity(os.getpid()),generation=b['generation']))
            receipt['consumed_by']=os.getpid();manage.write(self.data/'prepare.json',receipt)
            self.snapshot=b
        if not self.up:self.up=Upstream(self.data,b['project'],self.protocol)
        return text({'connected':True,'project':b['project'],'generation':b['generation']})
    def call(self,id,params):
        name=params.get('name');args=params.get('arguments',{})
        if not self.busy.acquire(False):
            result(id,text({'error':'单聊天顺序执行；前一请求未结束'},True));return
        key='request-'+uuid.uuid4().hex
        begun=False
        try:
            if name=='seagent_connect':result(id,self.handshake(args));return
            if name not in {v['name'] for v in self.tools}:raise ValueError('未知工具')
            if self.snapshot is None:raise RuntimeError('尚未连接当前项目；先按setup技能从真实聊天cwd执行prepare/start，再seagent_connect')
            with manage.locked(self.data):
                manage.guard(self.data,self.snapshot)
                jobs=manage.pending(self.data)
                # Unknown/suspended jobs may only be queried; never replay business writes.
                if jobs and name not in ('get_rpc_status','get_async_status','list_documents'):
                    raise RuntimeError('已有在途/未知任务，只允许查询状态，不重试写操作')
                jobs[key]={'state':'inflight','tool':name,'generation':self.snapshot['generation'],'bridge_pid':os.getpid()}
                manage.write(self.data/'pending.json',jobs);begun=True
            rid='up-'+uuid.uuid4().hex;self.ids[id]=rid
            r=self.up.call({'method':'tools/call','params':params},rid)
            with manage.locked(self.data):
                jobs=manage.pending(self.data);jobs.pop(key,None)
                serialized=json.dumps(r,ensure_ascii=False).lower()
                uncertain=(('error' in r or r.get('result',{}).get('isError',False)) and name not in ('get_async_status','get_rpc_status','list_documents') and any(w in serialized for w in ('timed out','timeout','cancelled','canceled','超时','connection reset','connection refused','broken pipe','eof','remote disconnected','connection aborted','connection closed','failed to connect','transport closed')))
                payloads=[]
                texts='\n'.join(c.get('text','') for c in r.get('result',{}).get('content',[]) if c.get('type')=='text')
                if name=='execute_code_async' and not r.get('result',{}).get('isError'):
                    match=re.search(r'\(job_id: ([^)]+)\)',texts)
                    if match:jobs[match.group(1)]={'state':'running','generation':self.snapshot['generation'],'tool':name}
                    else:uncertain=True
                if name=='get_async_status':
                    match=re.search(r'^Async job (\S+): (\w+)',texts,re.M)
                    if match and match.group(2) in ('done','completed','failed','error','cancelled','canceled'):jobs.pop(match.group(1),None)
                for c in r.get('result',{}).get('content',[]):
                    if c.get('type')=='text':
                        try:payloads.append(json.loads(c['text']))
                        except (ValueError,TypeError):pass
                def walk(x):
                    if isinstance(x,dict):
                        yield x
                        for y in x.values():yield from walk(y)
                    elif isinstance(x,list):
                        for y in x:yield from walk(y)
                for payload in payloads:
                    for v in walk(payload):
                        job=v.get('job_id') or (v.get('id') if name=='get_async_status' else None)
                        state=v.get('state') or v.get('status')
                        if isinstance(job,str):
                            if state in ('done','completed','failed','error','cancelled','canceled'):jobs.pop(job,None)
                            else:jobs[job]={'state':state or 'unknown','generation':self.snapshot['generation'],'tool':'execute_code_async'}
                if uncertain:jobs[key]={'state':'unknown','tool':name,'generation':self.snapshot['generation']}
                manage.write(self.data/'pending.json',jobs)
            r['id']=id;send(r)  # Preserve content, ImageContent, structuredContent, errors.
        except Exception as e:
            # An interrupted upstream request retains inflight entry for manual diagnosis.
            result(id,text({'error':str(e),'request_may_be_pending':begun},True))
        finally:
            self.ids.pop(id,None);self.busy.release()
    def handle(self,v):
        id=v.get('id');method=v.get('method');params=v.get('params',{})
        if id is None:
            if method=='notifications/cancelled' and self.up:
                rid=self.ids.get(params.get('requestId'))
                if rid:self.up.notify({'method':method,'params':dict(params,requestId=rid)})
            elif self.up and method!='notifications/initialized':self.up.notify({'method':method,'params':params})
            return
        if method=='initialize':
            requested=params.get('protocolVersion');self.protocol=requested if requested in SUPPORTED else '2025-11-25'
            result(id,{'protocolVersion':self.protocol,'capabilities':{'tools':{}},'serverInfo':{'name':'seagent-freecad-management','version':'0.2.0'}})
        elif method=='ping':result(id,{})
        elif method=='tools/list':
            management={'name':'seagent_connect','description':'Bind this MCP connection using marker returned by current project exec prepare; management only, no CAD edits.',
                        'inputSchema':{'type':'object','properties':{'marker':{'type':'string'}},'required':['marker'],'additionalProperties':False}}
            result(id,{'tools':self.tools+[management]})
        elif method=='tools/call':threading.Thread(target=self.call,args=(id,params),daemon=True).start()
        elif method in ('resources/list','resources/templates/list','prompts/list'):
            result(id,{'resourceTemplates':[]} if method=='resources/templates/list' else {method.split('/')[0]:[]})
        else:error(id,-32601,'Unsupported method')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data');a=ap.parse_args();bridge=Bridge(manage.root(a.data))
    try:
        for line in sys.stdin:
            try:bridge.handle(json.loads(line))
            except (ValueError,KeyError,TypeError) as e:error(None,-32700,str(e))
    finally:
        if bridge.up:bridge.up.close()

if __name__=='__main__':main()
