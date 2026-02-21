# Parse token:guildid:channelid:mute:deaf:stream:cam
import requests
import websocket
import json
import threading
import time
import random
import os
from pystyle import Colors, Colorate


active_tokens = []
last_token_count = 0

def voice_joiner():
    os.system("title Voice Joiner I Made By Quarz" if os.name == "nt" else "echo -ne '\033]0;Voice Joiner\007'")
    os.system("cls" if os.name == "nt" else "clear")
    
    ascii_text = r"""
 _    __      _                  __      _                
| |  / /___  (_)_______         / /___  (_)___  ___  _____
| | / / __ \/ / ___/ _ \   __  / / __ \/ / __ \/ _ \/ ___/
| |/ / /_/ / / /__/  __/  / /_/ / /_/ / / / / /  __/ /    
|___/\____/_/\___/\___/   \____/\____/_/_/ /_/\___/_/     
                                                          
"""
    
    terminal_width = os.get_terminal_size().columns
    lines = ascii_text.split('\n')
    centered_lines = [line.center(terminal_width) for line in lines]
    centered_text = '\n'.join(centered_lines)
    
    print(Colorate.Horizontal(Colors.black_to_green, centered_text))

    global active_tokens, last_token_count
    
    try:
        with open('tokens.txt', 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if not lines:
            print("[-] No tokens Found")
            return
        

        token_configs = []
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 8:
                config = {
                    'token': parts[0],
                    'guild_id': parts[1],
                    'channel_id': parts[2],
                    'mute': parts[3].lower() == 'true',
                    'deaf': parts[4].lower() == 'true',
                    'stream': parts[5].lower() == 'true',
                    'cam': parts[6].lower() == 'true',
                    'spotify': parts[7].lower() == 'true'
                }
                token_configs.append(config)
        
        if not token_configs:
            print("[-] No valid token configs found")
            return
            
        print(Colorate.Horizontal(Colors.green_to_white, f"[+] {len(token_configs)} tokens loaded"))
    except FileNotFoundError:
        print("[-] tokens.txt not found")
        return
    


    def connect_voice(config, index):
        token = config['token']
        guild_id = config['guild_id']
        channel_id = config['channel_id']
        mute = config['mute']
        deaf = config['deaf']
        fake_stream = config['stream']
        fake_cam = config['cam']
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        heartbeat_thread = None
        
        def on_message(ws, message):
            nonlocal reconnect_attempts, heartbeat_thread
            try:
                data = json.loads(message)
                if data.get('op') == 10:  
                    heartbeat_interval = data['d']['heartbeat_interval']
                    if heartbeat_thread and heartbeat_thread.is_alive():
                        heartbeat_thread.do_run = False
                    heartbeat_thread = threading.Thread(target=heartbeat, args=(ws, heartbeat_interval))
                    heartbeat_thread.daemon = True
                    heartbeat_thread.start()
                    

                    status_options = ["dnd", "idle"]
                    random_status = random.choice(status_options)
                    

                    identify = {
                        "op": 2,
                        "d": {
                            "token": token,
                            "properties": {
                                "$os": "Windows",
                                "$browser": "Discord Client",
                                "$device": "desktop"
                            },
                            "presence": {
                                "status": random_status,
                                "since": 0,
                                "activities": [],
                                "afk": False
                            }
                        }
                    }
                    ws.send(json.dumps(identify))
                
                elif data.get('op') == 0 and data.get('t') == 'READY':
                    reconnect_attempts = 0  
                    voice_state = {
                        "op": 4,
                        "d": {
                            "guild_id": guild_id,
                            "channel_id": channel_id,
                            "self_mute": mute,
                            "self_deaf": deaf,
                            "self_video": fake_cam,
                            "self_stream": fake_stream
                        }
                    }
                    ws.send(json.dumps(voice_state))
                    
                    status = "joined voice channel"
                    if fake_stream:
                        status += " with stream"
                    if fake_cam:
                        status += " with camera"
                    print(f"[+] Token {index+1} {status}")
                    
                elif data.get('op') == 11:  
                    pass  
                    
            except Exception as e:
                print(f"[-] Token {index+1} message error: {e}")
        
        def on_error(ws, error):
            error_str = str(error)
            if "Authentication failed" not in error_str and "WinError 10054" not in error_str:
                print(f"[-] Token {index+1} error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            nonlocal reconnect_attempts, heartbeat_thread
            if heartbeat_thread and heartbeat_thread.is_alive():
                heartbeat_thread.do_run = False
            

            if close_msg and b"Authentication failed" in close_msg:
                return
            
            if reconnect_attempts < max_reconnect_attempts:
                reconnect_attempts += 1
                wait_time = min(2 ** reconnect_attempts, 60)
                time.sleep(wait_time)
                connect_voice(config, index)
        
        def heartbeat(ws, interval):
            t = threading.current_thread()
            while getattr(t, "do_run", True):
                try:
                    time.sleep(interval / 1000)
                    if ws.sock and ws.sock.connected:
                        ws.send(json.dumps({"op": 1, "d": None}))
                    else:
                        break
                except Exception as e:
                    print(f"[-] Token {index+1} heartbeat error: {e}")
                    break
        
        try:
            ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=9&encoding=json",
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            if "Authentication failed" not in str(e):
                print(f"[-] Token {index+1} connection failed: {e}")
            if reconnect_attempts < max_reconnect_attempts and "Authentication failed" not in str(e):
                time.sleep(5)
                connect_voice(config, index)
    
    for i, config in enumerate(token_configs):
        threading.Thread(target=connect_voice, args=(config, i), daemon=True).start()
        time.sleep(1)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[+] Voice connections stopped")

if __name__ == "__main__":
    voice_joiner()
