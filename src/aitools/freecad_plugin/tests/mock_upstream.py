"""Synthetic protocol peer. No sockets, FreeCAD imports, files or CAD operations."""
import json
import sys
for line in sys.stdin:
    v=json.loads(line);method=v.get('method')
    if 'id'not in v:continue
    if method=='initialize':r={'protocolVersion':v['params']['protocolVersion'],'capabilities':{'tools':{}},'serverInfo':{'name':'synthetic-peer','version':'1'}}
    elif method=='tools/call':
        print(json.dumps({'jsonrpc':'2.0','method':'notifications/progress','params':{'progressToken':'test','progress':1}}),flush=True)
        r={'content':[{'type':'image','mimeType':'image/png','data':'AAAA'}],'structuredContent':{'args':v['params'].get('arguments')},'isError':False}
    else:r={}
    print(json.dumps({'jsonrpc':'2.0','id':v['id'],'result':r}),flush=True)
