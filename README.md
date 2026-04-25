========================================
Multi-thread Web Server - COMP 2322 Project
========================================

Student Name: [填写你的名字]
Student ID: [填写你的学号]

========================================
How to Run
========================================

1. Make sure Python 3.6+ is installed
2. Open terminal / PowerShell in the project folder
3. Run: python server.py
4. Open browser and visit: http://127.0.0.1:8080/

========================================
Test Commands (PowerShell)
========================================

[200 OK]
(Invoke-WebRequest -Uri "http://127.0.0.1:8080/test.txt" -UseBasicParsing).StatusCode

[304 Not Modified]
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /test.txt HTTP/1.1`r`nHost: 127.0.0.1`r`nIf-Modified-Since: Mon, 01 Jan 2090 00:00:00 GMT`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[403 Forbidden]
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /../server.py HTTP/1.1`r`nHost: 127.0.0.1`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[404 Not Found]
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /notexist.html HTTP/1.1`r`nHost: 127.0.0.1`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[400 Bad Request]
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("INVALID`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

========================================
Features Implemented
========================================

- Multi-threading (each request in a new thread)
- GET method for text files (test.txt)
- GET method for image files (test.jpg)
- HEAD method
- HTTP status codes: 200, 400, 403, 404, 304
- Last-Modified header
- If-Modified-Since header (304 response)
- Connection header (keep-alive / close)
- Request logging (server.log)

========================================
Log File Format
========================================

IP | Timestamp | Requested File | Status Code

Example:
127.0.0.1 | 2026-04-26 15:30:00 | /test.txt | 200

========================================
GitHub Repository
========================================

[填写你的 GitHub 链接]
