import sys
sys.path.insert(0, ".")
import asyncio, json
from services.gateway.main import app

async def test_asgi():
    response_started = {}
    response_body = []
    
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': 'GET',
        'path': '/healthz',
        'raw_path': b'/healthz',
        'query_string': b'',
        'headers': [],
        'client': ('127.0.0.1', 12345),
        'server': ('testserver', 80),
    }
    
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}
        
    async def send(message):
        if message['type'] == 'http.response.start':
            response_started.update(message)
        elif message['type'] == 'http.response.body':
            response_body.append(message.get('body', b''))
            
    await app(scope, receive, send)
    body_text = b''.join(response_body).decode('utf-8')
    print('STATUS:', response_started.get('status'))
    print('BODY:', body_text)

if __name__ == "__main__":
    asyncio.run(test_asgi())
    print("PURE ASGI TEST SUCCEEDED INSTANTLY!")
