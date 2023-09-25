from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import requests
import traceback
from monitor import start_monitor, create_monitor
import threading
import logging
import queue

route_table = [
        {
            'node': 'ubuntuDockerWorker', 
            'ip': '192.168.56.103', 
            'port': 8080,
            'status': 'N'
        },
        {
            'node': 'ubuntuDockerWorker1',
            'ip': '192.168.56.104', 
            'port': 8080,
            'status': 'Y'
        }
    ]


request_queue = queue.Queue()

class RoutingHandler(BaseHTTPRequestHandler):
    
    def __init__(self, request, client_address, server):
        self.route_table = route_table
        super().__init__(request, client_address, server)

    def log_message(self, format, *args):
        # print(self.headers['Host'])
        pass
    

    def __parse(self):
        content_length = int(self.headers['Content-Length'])
        get_data = self.rfile.read(content_length)

        # parse to json
        data = json.loads(get_data)
        return data

    def do_GET(self):
        # get request and put into request queue
        request_queue.put(self.__parse())

        for node in route_table:

            # select node
            if node['status'] == 'Y':
                target_address = f"{node['ip']}:{node['port']}" 

                url = f"http://{target_address}"

                response_content = ""

                error_response = {
                    'code': 500,
                    'status': 'failed'
                }
                

                # for selected node address send 
                try:
                    response_from_server = requests.get(url, json=request_queue.get())

                    response_content = response_from_server.text

                    print(response_content)

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()

                    self.wfile.write(response_content.encode('utf-8'))

                except:
                    response_content = json.dumps(error_response)
                    print('Response Error!')



def create_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    return logger


def server_run(logger):

    try:
        router_address = ('192.168.56.102', 8080)
        httpd = HTTPServer(router_address, RoutingHandler)

        logger.debug("Router Started...")
        httpd.serve_forever()
    except:
        traceback.print_exc()
        logger.debug("Router stopped")


def monitor_run(logger):
    # with yield in <start_monitor>
    generator = start_monitor(nodes_info=create_monitor())
    while True:
        # msg content style:
        #   {'node': node['name'], 'status': 'running', 'request': 'HS'}
        #
        msg = next(generator)
        logger.debug(msg)
        logger.debug(route_table)

        if msg is not None and msg['request'] == 'HS':
            change_node_status(route_table=route_table)



def change_node_status(route_table):

    ret = {
        'node': "",
        'operation': 'status change',
        'result': 'None'
    }

    for node_obj in route_table:
        # start node to run
        ret['node'] = node_obj['node']
        if node_obj['status'] == 'N':
            node_obj['status'] = 'Y'
            ret['result'] = 'success'
        else:
            ret['result'] = 'failed'

    return ret


def main():
    server_logger = create_logger("ServerLogger")
    monitor_logger = create_logger("MonitorLogger")

    server_thread = threading.Thread(target=server_run, args=((server_logger, )))
    monitor_thread = threading.Thread(target=monitor_run, args=((monitor_logger, )))

    monitor_thread.daemon = True

    server_thread.start()
    monitor_thread.start()

if __name__ == "__main__":
    
    try:
        main()
    except:
        print("Router stopped")
    