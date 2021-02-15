import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

logger = logging.getLogger('docserv')


class RESTServer(BaseHTTPRequestHandler):
    def _set_headers(self, mime = 'json'):
        self.send_response(200)
        mimetype = 'application/json'
        if mime == 'html':
            mimetype = 'text/html'
        self.send_header('Content-type', mimetype)
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self._set_headers(mime='html')
            self.wfile.write(
                bytes("<html><head><title>DocServ2 Build Server</title></head><body><h1>DocServ2 API</h1><p>GET information:</p><ul><li>Current Queue: /build_instructions/</li><li>Available Documents: /deliverables/</li></ul><p>To build, POST a JSON like [{\"docset\": \"15ga\", \"lang\": \"en-us\", \"product\": \"sles\", \"target\": \"external\"}] without a path</p></body></html>", 'utf-8'))
        elif self.path == '/build_instructions' or self.path == '/build_instructions/':
            self._set_headers()
            self.wfile.write(
                bytes(json.dumps(self.server.docserv.dict()), "utf-8"))
        elif self.path == '/deliverables' or self.path == '/deliverables/':
            self._set_headers()
            self.wfile.write(
                bytes(json.dumps(self.server.docserv.deliverables), "utf-8"))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        # [{"docset": "15ga", "lang": "en-us", "product": "sles", "target": "external"}]
        post_data = self.rfile.read(content_length)
        build_jobs = json.loads(post_data)
        for job in build_jobs:
            if self.server.docserv.queue_build_instruction(job):
                logger.info("Queueing %s", json.dumps(job))
            else:
                logger.info("Not queueing %s", json.dumps(job))
        self._set_headers()


class ThreadedRESTServer(ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, docserv, bind_and_activate=True):
        HTTPServer.__init__(self, server_address,
                            RequestHandlerClass, bind_and_activate)
        logger.info("Starting HTTP server on %s:%i",
                    server_address[0], server_address[1])
        self.docserv = docserv
