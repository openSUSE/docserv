import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

logger = logging.getLogger('docserv')


class RESTServer(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/build_instructions/':
            self._set_headers()
            self.wfile.write(
                bytes(json.dumps(self.server.docserv.dict()), "utf-8"))
        elif self.path == '/deliverables/':
            self._set_headers()
            self.wfile.write(
                bytes(json.dumps(self.server.docserv.deliverables), "utf-8"))

    def do_POST(self):
        logger.debug("Received POST request")

        if self.path == "/":
            self.handle_build()
        elif self.path == "/metadata":
            self.handle_metadata()
        else:
            self.send_error(404, "Not Found")

    def handle_build(self):
        content_length = int(self.headers['Content-Length'])
        # [{"docset": "15ga", "lang": "en-us", "product": "sles", "target": "external"}. ]
        post_data = self.rfile.read(content_length)
        logger.debug("Received POST data: %s", post_data)
        try:
            build_jobs = json.loads(post_data)
            for job in build_jobs:
                if self.server.docserv.queue_build_instruction(job):
                    logger.info("Queueing %s", json.dumps(job))
                else:
                    logger.info("Not queueing %s", json.dumps(job))
            # self._set_headers()
            return self.send_response(200)
        except json.decoder.JSONDecodeError:
            # do not print the details of the request, when we add an
            # authentication thing here, we may not be able to scrub the
            # password from a malformed request easily.
            logger.warning("Invalid JSON data submitted to REST API as build instruction. Ignoring.")
            self.send_error(400, "Invalid JSON data")

    def handle_metadata(self):
        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(data)
        logger.debug("Received POST data: %s", data)
        # Process the data and respond
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        response = ["Building metadata for:"]
        for item in data:
            response.append(
                f" * {item['target']}:{item['product']}/{item['docset']}/{item['lang']}\n"
                )
        self.wfile.write("\n".join(response).encode('utf-8'))


class ThreadedRESTServer(ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, docserv, bind_and_activate=True):
        HTTPServer.__init__(self, server_address,
                            RequestHandlerClass, bind_and_activate)
        logger.info("Starting HTTP server on %s:%i",
                    server_address[0], server_address[1])
        self.docserv = docserv
