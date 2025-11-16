import socket
import time
import subprocess
import sys
import os

HOST = '127.0.0.1'
PORT = 5555


def recv_until(sock, substr, timeout=5):
    """Receive data until substring found or timeout."""
    sock.settimeout(timeout)
    data = ''
    try:
        while True:
            chunk = sock.recv(1024).decode('utf-8', errors='ignore')
            if not chunk:
                break
            data += chunk
            if substr in data:
                break
    except socket.timeout:
        pass
    except Exception:
        pass
    return data


def test_game():
    print("=" * 70)
    print("AUTOMATED GAME TEST: Búa Kéo Bao Online")
    print("=" * 70)
    
    # Start server
    print("\n[1] Starting server...")
    server_proc = subprocess.Popen(
        [sys.executable, 'server.py'],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # Wait for server to start
    for i in range(10):
        time.sleep(0.5)
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(1)
            test_sock.connect((HOST, PORT))
            test_sock.close()
            print("[✓] Server listening on %s:%d" % (HOST, PORT))
            break
        except:
            pass
    else:
        print("[✗] Server failed to start")
        server_proc.terminate()
        return
    
    try:
        # Connect clients
        print("\n[2] Connecting Client 1...")
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.settimeout(10)
        s1.connect((HOST, PORT))
        print("[✓] Client 1 connected")
        
        time.sleep(0.3)
        
        print("\n[3] Connecting Client 2...")
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(10)
        s2.connect((HOST, PORT))
        print("[✓] Client 2 connected")
        
        # Exchange names
        print("\n[4] Client 1 sends name...")
        ask1 = recv_until(s1, ':', timeout=5)
        s1.sendall(b'Player1\n')
        msg1 = recv_until(s1, 'đợi', timeout=5)
        print("  ✓ Queued")
        
        time.sleep(0.3)
        
        print("\n[5] Client 2 sends name...")
        ask2 = recv_until(s2, ':', timeout=5)
        s2.sendall(b'Player2\n')
        msg2 = recv_until(s2, 'đấu', timeout=5)
        print("  ✓ Game started")
        
        time.sleep(0.5)
        
        # Get game prompts
        print("\n[6] Both clients receive choice prompt...")
        extra1 = recv_until(s1, 'Chọn:', timeout=5)
        extra2 = recv_until(s2, 'Chọn:', timeout=5)
        print("  ✓ Prompts received")
        
        # Send choices
        print("\n[7] Client 1 plays Đá (1), Client 2 plays Kéo (2)...")
        s1.sendall(b'1\n')
        s2.sendall(b'2\n')
        print("  ✓ Choices sent")
        
        time.sleep(0.5)
        
        # Read results
        print("\n[8] Reading game results...")
        result1 = recv_until(s1, 'thắng', timeout=5)
        result2 = recv_until(s2, 'thắng', timeout=5)
        
        print("  Client 1 result:")
        for line in result1.split('\n'):
            if line.strip():
                print("    " + line)
        
        print("\n  Client 2 result:")
        for line in result2.split('\n'):
            if line.strip():
                print("    " + line)
        
        # Verify
        print("\n[9] Verifying results...")
        checks = [
            ("Both see 'Player1 ra:'", "Player1 ra:" in result1 and "Player1 ra:" in result2),
            ("Both see 'Player2 ra:'", "Player2 ra:" in result1 and "Player2 ra:" in result2),
            ("Both see 'Đá'", "Đá" in result1 and "Đá" in result2),
            ("Both see 'Kéo'", "Kéo" in result1 and "Kéo" in result2),
            ("Both see 'Player1 thắng'", "Player1 thắng" in result1 and "Player1 thắng" in result2),
        ]
        
        passed = 0
        for check_name, result in checks:
            status = "[✓]" if result else "[✗]"
            print("  %s %s" % (status, check_name))
            if result:
                passed += 1
        
        print("\n" + "=" * 70)
        if passed == len(checks):
            print("SUCCESS! %d/%d checks passed - Fix is working!" % (passed, len(checks)))
        else:
            print("PARTIAL: %d/%d checks passed" % (passed, len(checks)))
        print("=" * 70)
        
        # Cleanup
        try:
            s1.close()
        except:
            pass
        try:
            s2.close()
        except:
            pass
    
    finally:
        print("\n[10] Stopping server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=2)
        except:
            server_proc.kill()
        print("[✓] Server stopped\n")


if __name__ == '__main__':
    test_game()
