========================================
How to Run
========================================

1. Make sure Python is installed
2. Open terminal
3. Run: python server.py
4. Visit: http://127.0.0.1:8080/

========================================
How to Test
========================================

[200 OK]
Browser: 
http://127.0.0.1:8080/test.txt
http://127.0.0.1:8080/test.jpg  //Place test.jpg in the ./www folder before running the server
PowerShell:
(Invoke-WebRequest -Uri "http://127.0.0.1:8080/test.txt" -UseBasicParsing).StatusCode

[400 Bad Request]
PowerShell:
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("INVALID`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[403 Forbidden]
PowerShell:
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /../server.py HTTP/1.1`r`nHost: 127.0.0.1`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[404 Not Found]
Browser: 
http://127.0.0.1:8080/xxx.html
PowerShell:
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /notexist.html HTTP/1.1`r`nHost: 127.0.0.1`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()

[304 Not Modified]
PowerShell:
$tcp = New-Object System.Net.Sockets.TcpClient; $tcp.Connect('127.0.0.1',8080); $s=$tcp.GetStream(); $w=New-Object System.IO.StreamWriter($s); $w.Write("GET /test.txt HTTP/1.1`r`nHost: 127.0.0.1`r`nIf-Modified-Since: Mon, 01 Jan 2090 00:00:00 GMT`r`n`r`n"); $w.Flush(); Start-Sleep -Milliseconds 500; $r=New-Object System.IO.StreamReader($s); $r.ReadLine(); $tcp.Close()