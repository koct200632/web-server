import socket
import threading
import os
import time
import datetime
from urllib.parse import unquote

# Configuration
HOST = '127.0.0.1'
PORT = 8080
WEB_ROOT = os.path.abspath('./www')
LOG_FILE = 'server.log'
BUFFER_SIZE = 8192

# Thread-safe Logging
log_lock = threading.Lock()

def write_log(client_ip, request_file, status_code):
    """
    Write a log entry for each client request.
    Format: IP | Timestamp | Requested File | Status Code
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with log_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{client_ip} | {timestamp} | {request_file} | {status_code}\n")

# HTTP Request Parser
def parse_request(request_data):
    """
    Parse raw HTTP request string.
    Returns: (method, path, headers)
    - method: GET or HEAD
    - path: URL-decoded file path
    - headers: dictionary of HTTP headers
    """
    lines = request_data.split('\r\n')
    if not lines:
        return None, None, None
    
    # Parse request line: GET /index.html HTTP/1.1
    parts = lines[0].split(' ')
    if len(parts) != 3:
        return None, None, None
    
    method = parts[0]
    path = unquote(parts[1])
    
    # headers
    headers = {}
    for line in lines[1:]:
        if ': ' in line:
            k, v = line.split(': ', 1)
            headers[k] = v
    
    return method, path, headers

# MIME Type Helper
def get_mime_type(filepath):
    """
    Return Content-Type based on file extension.
    Used by browser to correctly display files.
    """
    ext = os.path.splitext(filepath)[1].lower()
    types = {
        '.html': 'text/html',
        '.txt': 'text/plain',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.css': 'text/css',
        '.js': 'application/javascript'
    }
    return types.get(ext, 'application/octet-stream')

# Error Response
def generate_error_response(status_code, message):
    """
    Generate HTTP error response with HTML body.
    Supports: 400 Bad Request, 403 Forbidden, 404 Not Found
    """
    status_text = {
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found'
    }.get(status_code, 'Error')
    
    # HTML error page
    body = f'<html><body><h1>{status_code} {status_text}</h1><p>{message}</p></body></html>'
    
    # Build HTTP response
    response = f'HTTP/1.1 {status_code} {status_text}\r\n'
    response += 'Content-Type: text/html\r\n'
    response += f'Content-Length: {len(body)}\r\n'
    response += 'Connection: close\r\n\r\n'
    response += body
    
    return response.encode()

# Main Response
def generate_response(method, path, headers):
    """
    Generate HTTP response for valid requests.
    Returns: (response_bytes, status_code, should_close)
    
    Handles:
    - 200 OK: File exists and is returned
    - 304 Not Modified: If-Modified-Since header matches
    - 403 Forbidden: Path traversal detection
    - 404 Not Found: File does not exist
    """
    
    # Security Check
    # Detect directory traversal attacks (../)
    if '..' in path:
        return generate_error_response(403, 'Forbidden - Directory traversal'), 403, True
    
    # Handle Root Path
    if path == '/' or path == '':
        path = '/index.html'
    if path.startswith('/'):
        path = path[1:]
    
    # Build Safe File Path
    safe_path = os.path.join(WEB_ROOT, path)
    safe_path = os.path.normpath(safe_path)
    
    # Double-check
    if not safe_path.startswith(WEB_ROOT):
        return generate_error_response(403, 'Forbidden'), 403, True
    
    # File Existence Check
    if not os.path.exists(safe_path):
        return generate_error_response(404, 'Not Found'), 404, True
    
    # Handle directory: look for index.html
    if os.path.isdir(safe_path):
        safe_path = os.path.join(safe_path, 'index.html')
        if not os.path.exists(safe_path):
            return generate_error_response(404, 'Not Found'), 404, True
    
    # Get File Metadata
    stat = os.stat(safe_path)
    last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(stat.st_mtime))
    content_length = stat.st_size
    
    # Handle If-Modified-Since (304)
    if 'If-Modified-Since' in headers:
        try:
            # Parse client's timestamp
            client_time = time.strptime(headers['If-Modified-Since'], '%a, %d %b %Y %H:%M:%S GMT')
            client_stamp = time.mktime(client_time)
            
            # If file hasn't changed, return 304
            if stat.st_mtime <= client_stamp + 1:   # +1 second tolerance
                resp = 'HTTP/1.1 304 Not Modified\r\n'
                resp += 'Server: MyWebServer\r\n'
                resp += f'Date: {time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())}\r\n'
                resp += 'Connection: keep-alive\r\n\r\n'
                return resp.encode(), 304, False
        except:
            pass    # Parse error: ignore and continue with 200
    
    # Handle HEAD Request
    is_head = (method == 'HEAD')
    
    # Build Success Response Headers
    response = 'HTTP/1.1 200 OK\r\n'
    response += f'Content-Type: {get_mime_type(safe_path)}\r\n'
    response += f'Content-Length: {content_length}\r\n'
    response += f'Last-Modified: {last_modified}\r\n'
    
    # Handle Connection header
    should_close = False
    if 'Connection' in headers and headers['Connection'].lower() == 'close':
        should_close = True
        response += 'Connection: close\r\n'
    else:
        response += 'Connection: keep-alive\r\n'
    
    response += '\r\n'
    
    # HEAD: Return headers only
    if is_head:
        return response.encode(), 200, should_close
    
    # GET: Read and return file content
    with open(safe_path, 'rb') as f:
        body = f.read()
    
    return response.encode() + body, 200, should_close

# Client Handler
def handle_client(conn, addr):
    """
    Handle a single client connection.
    Runs in its own thread for concurrency.
    """
    try:
        conn.settimeout(5)
        
        # Receive HTTP request
        data = b''
        while True:
            chunk = conn.recv(BUFFER_SIZE)
            if not chunk:
                break
            data += chunk
            if b'\r\n\r\n' in data:    # End of headers
                break
        
        if not data:
            conn.close()
            return
        
        # Decode request
        try:
            request_str = data.decode('utf-8', errors='ignore')
        except:
            request_str = data.decode('latin-1')
        
        # Parse request
        method, path, headers = parse_request(request_str)
        
        # 400 Bad Request: Invalid request line
        if method is None:
            response = generate_error_response(400, 'Malformed request line')
            conn.sendall(response)
            write_log(addr[0], 'unknown', 400)
            conn.close()
            return
        
        # 400 Bad Request: Unsupported method
        if method not in ['GET', 'HEAD']:
            response = generate_error_response(400, 'Method not allowed')
            conn.sendall(response)
            write_log(addr[0], path, 400)
            conn.close()
            return
        
        # Generate and send response
        response, code, should_close = generate_response(method, path, headers)
        conn.sendall(response)
        
        # Log the request
        write_log(addr[0], path, code)
        
        # Close connection if needed
        if should_close:
            conn.close()
        else:
            conn.close()
            
    except Exception as e:
        print(f"Error: {e}")
        conn.close()

# Server Entry Point
def start_server():
    """
    Initialize and start the web server.
    Creates web root directory and test files if they don't exist.
    """
    # Create web root and test files
    if not os.path.exists(WEB_ROOT):
        os.makedirs(WEB_ROOT)
        with open(os.path.join(WEB_ROOT, 'index.html'), 'w') as f:
            f.write('<h1>Welcome to My Web Server</h1>')
        with open(os.path.join(WEB_ROOT, 'test.txt'), 'w') as f:
            f.write('This is a test file for 200 OK response.')
        print(f"[INFO] Created {WEB_ROOT}/ with index.html and test.txt")
    
    # Initialize log file
    with open(LOG_FILE, 'w') as f:
        f.write("=== Web Server Log ===\n")
        f.write("Format: IP | Timestamp | Requested File | Status Code\n")
    
    # Create listening socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    server.bind((HOST, PORT))
    server.listen(10)
    
    print(f"\n[INFO] Server started successfully!")
    print(f"[INFO] Address: http://{HOST}:{PORT}")
    print(f"[INFO] Web root: {WEB_ROOT}")
    print(f"[INFO] Log file: {os.path.abspath(LOG_FILE)}")
    print(f"[INFO] Press Ctrl+C to stop\n")
    
    # Main loop: accept connections and spawn threads
    while True:
        conn, addr = server.accept()
        print(f"[CONNECTION] {addr}")
        
        # Create new thread for each client
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.daemon = True
        t.start()

# Program Entry
if __name__ == '__main__':
    start_server()