import subprocess
import time
import os
import requests
import pyuac
import sys
import vdf
import psutil
from datetime import datetime

#Based on  ejahdev's  https://github.com/ejahdev/Palworld-Powershell-Server-Manager

steam_path = r'PATH_TO_STEAM_CMD'  # insert path to steamcmd
steam_cmd = f"{steam_path}\\steamcmd.exe"
palworld_folder = f'PATH_TO_PALSERVER_DIR'  # insert path to PALSERVER

auto_update = True  # Set True or False if you want to auto-update your server during restarts

restart_interval = 86400  # 86400 - 24 hours in seconds, Need to replace this with a scheduled event
#Need to replace this with a scheduled event
backup_interval = [
    '00:01',
    '12:01'
] 
restart_warning = 60  # int in seconds before server restart a warning message is broadcasted to players

discord_webhook_enabled = True  # Set to True to enable Discord webhook messages, and False to disable it
tag_role_enabled = True  # Set to True to enable tagging a role in the webhook message when an update is found, and False to disable it
discord_role_id = "DISCORD_ROLE_ID"  # Replace with ID of the discord role to tag in webhook message.
discord_webhook_url = "DISCORD_WEBHOOK_URL"  # Change to your discord webhook url

arrcon_path = r'PATH_TO_ARRCON'  # Set to ARRCON.exe path
rcon_host = "127.0.0.1"  # change to your rcon host if not local
rcon_port = "25575"  # change to your desired port if not default
rcon_password = "ARRCON_PASSWD"  # Insert rcon password
broadcast_message = f"<@&{discord_role_id}> Server will restart in 1 minute!"  # Change as desired

log_file = f"PalServer-{datetime.now().strftime('%Y%m%d')}.txt"  # Creates log file in the same path as ps1 script
warning_sent = False  # do NOT change - makes sure the warning message doesn't send multiples

#@main_requires_admin  - Does not seem to work
def main():
    global warning_sent
    server_timer = 0
    backup_timer = 0
    while True:
    
        PalworldServerProc = findProcessIdByName("PalServer")
        if not PalworldServerProc:
            logme(f"[{datetime.now()}] Server Not Running. Starting Server.")
            start_server()
        else:
            logme(f"[{datetime.now()}] Server Running Normally.")

        time.sleep(60)
        server_timer += 60
        backup_timer += 60

        if server_timer >= (restart_interval - restart_warning) and not warning_sent:
            # Broadcast a warning message to users
            broadcast_message_to_discord(broadcast_message)
            logme(f"[{datetime.now()}] Broadcasting warning message to users.")
            warning_sent = True

        if server_timer >= restart_interval:
            logme(f"[{datetime.now()}] Restarting Server.")
            subprocess.run(["taskkill", "/F", "/IM", "PalServer-Win64-Test-Cmd.exe", "/T"])
            subprocess.run(["taskkill", "/F", "/IM", "PalServer.exe", "/T"])
            server_timer = 0       
            start_server()
            warning_sent = False
            broadcast_message_to_discord("Palworld Server Status",f"<@&{discord_role_id}> The server has restarted successfully.",65280)

        current_time = datetime.now().strftime('%H:%M')
        if current_time in backup_interval:
            logme(f"[{datetime.now()}] Backup Timer Reached. Starting Server Backup.")
            backup_timer = 0
            backup_server()

def update_server():
    if auto_update:
        try:
            api_response = requests.get("https://api.steamcmd.net/v1/info/2394010").json()
            last_checked_build_id = api_response["data"]["2394010"]["depots"]["branches"]["public"]["buildid"]
            logme(f"last_checked_build_id = {last_checked_build_id}")
            d = vdf.load(open(f"{steam_path}\\steamapps\\appmanifest_2394010.acf"))
            local_build_id = d['AppState']['buildid']
            logme(f"local_build_id = {local_build_id}")
            if last_checked_build_id > local_build_id:
                logme(f"[{datetime.now()}] Server Has an Update. Update Starting.")
                if tag_role_enabled:
                    broadcast_message_to_discord("Palworld Server Status",f""":palm_up_hand: :mirror_ball: :rooster: 
                    
                    <@&{discord_role_id}> Server has an update! Make sure to update your client!""",65280)
                else:
                    broadcast_message_to_discord("Palworld Server Status",f"<@&{discord_role_id}> Server has an update! Make sure to update your client!",65280)
                # Start the update process using SteamCMD
                subprocess.run(f"{steam_cmd} +@ShutdownOnFailedCommand 1 +@NoPromptForPassword 1 +login anonymous +app_update 2394010 validate +quit")
            else:
                logme(f"[{datetime.now()}] No Update Available. Starting Server.")
        except Exception as e:
            logme(f"[{datetime.now()}] Could not check for update. Logging error message. Make sure you have an internet connection. Starting server anyways.")
            logme(e)

def start_server():

    update_server()
    
    subprocess.Popen([f"{palworld_folder}\\PalServer.exe", "-useperfthreads", "-NoAsyncLoadingThread", "-UseMultithreadForDS"], creationflags=psutil.HIGH_PRIORITY_CLASS)
    
    time.sleep(20)
    # Set Priority of PalServer-Win64-Test-Cmd to High
    PalServerProc = findProcessIdByName("PalServer-Win64-Test-Cmd")
    PalServerProc.nice(psutil.HIGH_PRIORITY_CLASS)
    
    logme(f"found {PalServerProc.pid} - {PalServerProc.name()} <{PalServerProc.nice()}>")

    print(f"[{datetime.now()}] Server Started.")
    broadcast_message_to_discord("Palworld Server Status",f""":palm_up_hand: :mirror_ball: :rooster: 
    
    <@&{discord_role_id}> The server has started successfully.!""","65280")

    #main()

def backup_server():
    if not os.path.exists(f"{palworld_folder}\\Pal\\Saved\\SaveGames\\Backups"):
        os.makedirs(f"{palworld_folder}\\Pal\\Saved\\SaveGames\\Backups")
    date_time = datetime.now().strftime('%Y_%m-%d_%A_%I_%M_%p')
    # Perform the Robocopy operation
    try:
        subprocess.run([
            "robocopy.exe",
            f"{palworld_folder}\\Pal\\Saved\\SaveGames\\0",
            f"{palworld_folder}\\Pal\\Saved\\SaveGames\\Backups\\{date_time}",
            "/mir", "/b", "/r:0", "/copyall", "/dcopy:dat",
            "/xd", "'$Recycle.bin', 'system volume information'",
            "/xf", "'thumbs.db'",
            "/NFL", "/NDL", "/NJH", "/NJS", "/nc", "/ns", "/np",
            "/COPY:DAT"
        ], check=True)
        # Update the "Date Modified" attribute of the destination folder
        os.utime(f"{palworld_folder}\\Pal\\Saved\\SaveGames\\Backups\\{date_time}", None)
        logme(f"[{datetime.now()}] Server Backup Complete.")
    except Exception as e:
        logme(f"Error occurred during Robocopy: {e}")

def broadcast_message_to_discord(title,message,color):
    if discord_webhook_enabled:
        json_data = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color
            }]
        }
        try:
            requests.post(discord_webhook_url, json=json_data)
        except Exception as e:
            logme(f"Failed to send Discord webhook: {e}")

def logme(message):
    with open(f"{os.path.dirname(os.path.realpath(sys.argv[0]))}\\{log_file}", "a") as f:
        f.write(message + '\n')
        print(message)

def findProcessIdByName(processName):
    # Here is the list of all the PIDs of a all the running process 
    # whose name contains the given string processName
    processPid = ""
    #Iterating over the all the running process
    for proc in psutil.process_iter():
       try:
           pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
           # Checking if process name contains the given name string.
           if processName.lower() in pinfo['name'].lower() :
               processPid = proc
       except (psutil.NoSuchProcess, psutil.AccessDenied , psutil.ZombieProcess) :
           pass
    return processPid;
   
# Start the main loop
if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        logme("Re-launching as admin!")
        pyuac.runAsAdmin()
    else:        
        main()  # Already an admin here.
