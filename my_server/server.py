import socket
import threading
import os
import datetime
from email.utils import formatdate, parsedate_to_datetime

# Server configuration
HOST = '127.0.0.1'
PORT = 8080
WEB_ROOT = 'www'
LOG_FILE = 'log.txt'

def write_log(client_ip, requested_file, status_code):
    """Write request information to log file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{client_ip} | {timestamp} | {requested_file} | {status_code}\n")

def get_mime_type(file_path):
    """Return MIME type based on file extension"""
    if file_path.endswith('.html') or file_path.endswith('.htm'):
        return 'text/html'
    elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        return 'image/jpeg'
    elif file_path.endswith('.png'):
        return 'image/png'
    elif file_path.endswith('.gif'):
        return 'image/gif'
    else:
        return 'text/plain'

def get_last_modified(file_path):
    """Get last modified time of file in HTTP date format"""
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        return formatdate(mtime, usegmt=True)
    return None

def parse_request(request):
    """Parse HTTP request to get method, path, and headers"""
    lines = request.split('\r\n')
    if not lines:
        return None, None, None
    
    first_line = lines[0]
    parts = first_line.split()
    
    if len(parts) < 2:
        return None, None, None
    
    method = parts[0]
    path = parts[1]
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key] = value
    
    return method, path, headers

def send_response(client_socket, status_code, status_text, content_type, body, last_modified=None, connection_close=True):
    """Send HTTP response with headers and body"""
    response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    headers = f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body)}\r\n"
    
    if last_modified:
        headers += f"Last-Modified: {last_modified}\r\n"
    
    if connection_close:
        headers += "Connection: close\r\n"
    else:
        headers += "Connection: keep-alive\r\n"
    
    headers += "\r\n"
    
    client_socket.send(response_line.encode() + headers.encode() + body)

def send_error_response(client_socket, status_code, status_text, connection_close=True):
    """Send error response (403, 400, 404)"""
    body = f"<html><body><h1>{status_code} {status_text}</h1></body></html>".encode()
    send_response(client_socket, status_code, status_text, 'text/html', body, None, connection_close)

def handle_get(client_socket, path, headers, connection_close):
    """Handle GET request"""
    # Security: prevent directory traversal
    if '..' in path:
        send_error_response(client_socket, '403', 'Forbidden', connection_close)
        return '403'
    
    # Set default file
    if path == '/':
        path = '/index.html'
    
    file_path = WEB_ROOT + path
    
    # Check if file exists
    if not os.path.exists(file_path):
        send_error_response(client_socket, '404', 'Not Found', connection_close)
        return '404'
    
    # Get real last modified time of the file
    last_modified = get_last_modified(file_path)
    
    # Check for If-Modified-Since header (304 response)
    if 'If-Modified-Since' in headers and last_modified:
        if_modified = headers['If-Modified-Since']
        # Compare dates (simple string comparison works for same format)
        if if_modified == last_modified:
            # Send 304 Not Modified (no body)
            response_line = "HTTP/1.1 304 Not Modified\r\n"
            headers_resp = f"Last-Modified: {last_modified}\r\n"
            if connection_close:
                headers_resp += "Connection: close\r\n"
            else:
                headers_resp += "Connection: keep-alive\r\n"
            headers_resp += "\r\n"
            client_socket.send(response_line.encode() + headers_resp.encode())
            return '304'
    
    # Read and send file
    try:
        with open(file_path, 'rb') as f:
            body = f.read()
        
        content_type = get_mime_type(file_path)
        send_response(client_socket, '200', 'OK', content_type, body, last_modified, connection_close)
        return '200'
    except Exception:
        send_error_response(client_socket, '403', 'Forbidden', connection_close)
        return '403'

def handle_head(client_socket, path, headers, connection_close):
    """Handle HEAD request (same as GET but no body)"""
    # Security: prevent directory traversal
    if '..' in path:
        send_error_response(client_socket, '403', 'Forbidden', connection_close)
        return '403'
    
    if path == '/':
        path = '/index.html'
    
    file_path = WEB_ROOT + path
    
    if not os.path.exists(file_path):
        send_error_response(client_socket, '404', 'Not Found', connection_close)
        return '404'
    
    try:
        with open(file_path, 'rb') as f:
            body = f.read()
        
        content_type = get_mime_type(file_path)
        last_modified = get_last_modified(file_path)
        
        # Send only headers, no body
        response_line = "HTTP/1.1 200 OK\r\n"
        headers_resp = f"Content-Type: {content_type}\r\n"
        headers_resp += f"Content-Length: {len(body)}\r\n"
        headers_resp += f"Last-Modified: {last_modified}\r\n"
        
        if connection_close:
            headers_resp += "Connection: close\r\n"
        else:
            headers_resp += "Connection: keep-alive\r\n"
        
        headers_resp += "\r\n"
        client_socket.send(response_line.encode() + headers_resp.encode())
        return '200'
    except Exception:
        send_error_response(client_socket, '403', 'Forbidden', connection_close)
        return '403'

def handle_client(client_socket, client_addr):
    """Handle each client connection in a separate thread"""
    client_ip = client_addr[0]
    print(f"[Thread] Handling connection from {client_ip}")
    
    try:
        # Receive request
        request = client_socket.recv(4096).decode('utf-8', errors='ignore')
        
        if not request:
            client_socket.close()
            return
        
        print(f"\n[Request from {client_ip}]:\n{request[:500]}...")
        
        # Parse request
        method, path, headers = parse_request(request)
        
        if method is None:
            send_error_response(client_socket, '400', 'Bad Request', True)
            write_log(client_ip, 'unknown', '400')
            client_socket.close()
            return
        
        # Check Connection header
        connection_header = headers.get('Connection', '').lower()
        connection_close = (connection_header == 'close')
        
        # Handle different HTTP methods
        status_code = None
        
        if method == 'GET':
            status_code = handle_get(client_socket, path, headers, connection_close)
        elif method == 'HEAD':
            status_code = handle_head(client_socket, path, headers, connection_close)
        else:
            send_error_response(client_socket, '400', 'Bad Request', True)
            status_code = '400'
        
        # Write to log
        if status_code:
            write_log(client_ip, path, status_code)
        
    except Exception as e:
        print(f"[Error] {e}")
        try:
            send_error_response(client_socket, '400', 'Bad Request', True)
            write_log(client_addr[0], 'unknown', '400')
        except:
            pass
    
    finally:
        client_socket.close()
        print(f"[Thread] Connection from {client_ip} closed")

def main():
    """Main function to start the server"""
    # Create web root directory if it doesn't exist
    if not os.path.exists(WEB_ROOT):
        os.makedirs(WEB_ROOT)
        print(f"[Info] Created {WEB_ROOT} directory")
    
    # Create a sample index.html if it doesn't exist
    index_path = os.path.join(WEB_ROOT, 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write("""<html>
<head><title>My Web Server</title></head>
<body>
<h1>Hello! My Web Server is Working!</h1>
<p>This is index.html</p>
<hr>
<p>GET method: ✅ Working</p>
<p>404 error: ✅ Working</p>
</body>
</html>""")
        print(f"[Info] Created sample {index_path}")
    
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    
    print(f"\n{'='*50}")
    print(f"Web Server Started!")
    print(f"Address: http://{HOST}:{PORT}")
    print(f"Web Root: {WEB_ROOT}")
    print(f"Log File: {LOG_FILE}")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*50}\n")
    
    try:
        while True:
            client_socket, client_addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
            thread.daemon = True
            thread.start()
            print(f"[Main] Active threads: {threading.active_count() - 1}")
            
    except KeyboardInterrupt:
        print(f"\n[Info] Server shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()