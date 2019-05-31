import os
import platform
from time import sleep

from log import info, stopped, warning
from colorama import Fore
from ServerFunctions import check_server, get_channel_info, add_channel, remove_channel, get_settings, swap_settings, \
    get_youtube_settings, get_youtube_info, youtube_login, youtube_logout, test_upload

serverIP = None
serverPort = None

# Windows ToastNotifier
if platform.release() is '10':
    from win10toast import ToastNotifier

    toaster = ToastNotifier()
else:
    toaster = None


#
#
#
#
# THIS IS VERY POORLY CODED BUT IT WORKS.
#
#
#


def clearScreen():
    os.system('cls' if os.name == "nt" else 'clear')


# Windows Notification
def show_windows_toast_notification(title, description):
    if toaster is not None:
        toaster.show_toast(title, description, icon_path='python.ico')


if __name__ == '__main__':
    print("")
    print("What is the Server IP?")
    serverIP = input(":")
    print("What is the Server Port?")
    serverPort = input(":")
    info("Checking for Server port " + serverPort + " on " + serverIP)
    if not check_server(serverIP, serverPort):
        stopped("Server is not running! Try checking again.")
    else:
        info("Server Running.")
        info("Getting Server Info.")
        channel_info = get_channel_info(serverIP, serverPort)
        Screen = "Main"
        while True:
            if Screen is "Main":
                loopNumber = 1
                clearScreen()
                print("")
                if len(channel_info['channels']) is 0:
                    print(Fore.LIGHTMAGENTA_EX + "No Channels currently added in the list.")
                else:
                    print(Fore.LIGHTMAGENTA_EX + "List of Channels:")
                    print("")
                    for channel in channel_info['channels']:
                        channelInfo = channel_info['channel'][channel]
                        if channelInfo['name'] is None:
                            if 'error' in channelInfo:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channel +
                                      Fore.LIGHTRED_EX + " [FAILED GETTING YOUTUBE DATA]")
                            else:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channel +
                                      Fore.LIGHTRED_EX + " [GETTING YOUTUBE DATA]")
                        elif channelInfo['live'] is None:
                            print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                'name'] +
                                  Fore.LIGHTBLUE_EX + " [INTERNET OFFLINE]")
                        elif channelInfo['live'] is True:
                            if channelInfo['broadcastId'] is not None:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                    'name'] + Fore.LIGHTRED_EX + " [LIVE]" + Fore.LIGHTGREEN_EX + " Recording Status: "
                                      + channelInfo['recording_status'] + " " + Fore.LIGHTYELLOW_EX +
                                      "[RECORDING BROADCAST ID: " + channelInfo['broadcastId'] + "]")
                            else:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                    'name'] + Fore.LIGHTRED_EX + " [LIVE]" + Fore.LIGHTGREEN_EX + " Recording Status: "
                                      + channelInfo['recording_status'])
                        else:
                            if channelInfo['privateStream'] is True:
                                if channelInfo['sponsor_on_channel'] is True:
                                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE +
                                          channelInfo[
                                              'name'] + Fore.LIGHTRED_EX + " [PRIVATE] " + "[SPONSOR MODE (CHECKS "
                                                                                           "COMMUNITY TAB)]")
                                else:
                                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                        'name'] + Fore.LIGHTRED_EX + " [PRIVATE] " + Fore.WHITE + " ")
                            elif channelInfo['live_scheduled'] is True:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                    'name'] + Fore.LIGHTGREEN_EX + " [SCHEDULED AT " +
                                      channelInfo['live_scheduled_time'] + " (AT SERVER\'S TIMEZONE)]")
                            else:
                                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + channelInfo[
                                    'name'] + Fore.LIGHTCYAN_EX + " [NOT LIVE]")
                        loopNumber += 1
                print("")
                print(" 1) Refresh Channel List.")
                print(" 2) Add Channel")
                print(" 3) Remove Channel")
                print(" 4) Change Settings")
                if toaster is not None and 'localhost' not in serverIP:
                    print("N: Holds console, shows Windows 10 Toast Notification every time a stream goes live.")
                print("   Type a specific number to do the specific action. - ")
                option = input(":")
                if option is "1":  # Just Refresh
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    info("Getting Server Info.")
                    channel_info = get_channel_info(serverIP, serverPort)
                elif option is "2":  # ADDING CHANNELS
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    print("To Find The Channel_IDs USE THIS: ")
                    print("https://commentpicker.com/youtube-channel-id.php")
                    temp_channel_id = input("Channel ID: ")
                    ok, reply = add_channel(serverIP, serverPort, temp_channel_id)
                    del temp_channel_id
                    print("")
                    print("")
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    else:
                        print(Fore.LIGHTGREEN_EX + "Channel has now been added.")
                    print("")
                    input("Press enter to go back to Selection.")
                    # Refresh
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    info("Getting Server Info.")
                    channel_info = get_channel_info(serverIP, serverPort)
                elif option is "3":  # REMOVE CHANNELS (BETA ON SERVER)
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    print("  To Find The Channel_IDs USE THIS: ")
                    print("  https://commentpicker.com/youtube-channel-id.php")
                    temp_channel_id = input("Channel ID: ")
                    ok, reply = remove_channel(serverIP, serverPort, temp_channel_id)
                    del temp_channel_id
                    print("")
                    print("")
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    else:
                        print(Fore.LIGHTGREEN_EX + "Channel has now been removed.")
                    print("")
                    input("Press enter to go back to Selection.")
                    # Refresh
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    info("Getting Server Info.")
                    server_info = get_channel_info(serverIP, serverPort)
                elif option is "4":
                    Screen = "Settings"
                elif option is "N":  # WINDOWS 10 TOAST Notification HOLD
                    Screen = "NotificationHold"
            elif Screen is "Settings":
                print("")
                print("1) Upload Settings")
                print("2) Boolean Settings")
                option = input(":")
                if option is "2":
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    info("Getting Settings.")
                    settings = get_settings(serverIP, serverPort)
                    if settings == 404:
                        warning("It seems this server doesn't support getQuickSettings.")
                        sleep(2.5)
                    else:
                        Screen = "BooleanSettings"
                if option is "1":
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    info("Getting Settings.")
                    settings = get_youtube_settings(serverIP, serverPort)
                    info = get_youtube_info(serverIP, serverPort)
                    if settings == 404 or info == 404:
                        warning("It seems this server doesn't support UploadSettings.")
                        sleep(2.5)
                    else:
                        Screen = "UploadSettings"
            elif Screen is "BooleanSettings":
                clearScreen()
                print("")
                print("")
                print(Fore.LIGHTGREEN_EX + "List of Settings:")
                setting_array = []
                loopNumber = 1
                for setting in settings['settings']:
                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + setting +
                          Fore.LIGHTRED_EX + ": " + str(settings['settings'][setting]) + Fore.LIGHTYELLOW_EX +
                          " [SWITCH BOOLEAN]")
                    setting_array.append(setting)
                    loopNumber += 1
                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.LIGHTRED_EX + "EXIT" +
                      Fore.LIGHTRED_EX + ": " + " " + Fore.LIGHTYELLOW_EX + " [EXITS TO THE MAIN MENU]")
                exit_number = len(setting_array) + 1
                print("")
                print(Fore.LIGHTBLUE_EX + "  Type a setting number to do the specific action provided.")
                option = input(":")
                is_number = True
                try:
                    int(option)
                except ValueError:
                    print(Fore.LIGHTRED_EX + "That is not a number!")
                    is_number = False
                    sleep(3.5)
                if is_number:
                    option = int(option)
                    if option == exit_number:
                        Screen = "Main"
                    else:
                        is_good_index = True
                        try:
                            setting = setting_array[option - 1]
                        except IndexError:
                            print(Fore.LIGHTRED_EX + "Sorry, that number is out of range of the numbers listed!")
                            sleep(3.5)
                            is_good_index = False
                        if is_good_index:
                            if check_server(serverIP, serverPort) is False:
                                stopped("Lost Connection of the Server!")
                            reply = swap_settings(serverIP, serverPort, setting)
                            print("")
                            print("")
                            if reply == 404:
                                print(Fore.LIGHTRED_EX + "Sorry, the Server, doesn't support that type of setting"
                                                         " to be changed!")
                                sleep(3.5)
                            elif "OK" not in reply:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                sleep(3.5)
                            else:
                                info("Getting Settings.")
                                settings = get_settings(serverIP, serverPort)
            elif Screen is "UploadSettings":
                clearScreen()
                print("")
                print(Fore.LIGHTMAGENTA_EX + "List of Settings:")

                print("")

                if info['info']['YoutubeAccountLogin-in']:
                    print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount USING YOUTUBE API" +
                          Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                          + Fore.LIGHTYELLOW_EX + " [SIGN OUT (" + info['info']['YoutubeAccountName'] + ")]")
                else:
                    if settings['settings']['UploadLiveStreams']:
                        print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount" +
                              Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                              + Fore.LIGHTYELLOW_EX + " [LOGIN-IN] " + Fore.LIGHTRED_EX +
                              "[NEEDED FOR UploadLiveStreams TO WORK]")
                    else:
                        print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount" +
                              Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                              + Fore.LIGHTYELLOW_EX + " [LOGIN-IN] " + Fore.LIGHTRED_EX +
                              "[UploadLiveStreams NEEDS TO BE ENABLED FOR THIS TO WORK]")
                print("")
                if info['info']['YoutubeAccountLogin-in']:
                    print("    " + Fore.LIGHTCYAN_EX + str(2) + ": " + Fore.WHITE + "TestUpload" +
                          Fore.LIGHTRED_EX + ": " + ""
                          + Fore.LIGHTYELLOW_EX + "[RECORDS A CHANNEL FOR A FEW SECONDS]")
                else:
                    print("    " + Fore.LIGHTCYAN_EX + str(2) + ": " + Fore.WHITE + "TestUpload" +
                          Fore.LIGHTRED_EX + ": " + ""
                          + Fore.LIGHTRED_EX + "[DISABLED. NEED YOUTUBE ACCOUNT LOGIN-IN]")
                loopNumber = 3
                for setting in settings['settings']:
                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + setting +
                          Fore.LIGHTRED_EX + ": " + str(settings['settings'][setting]) + Fore.LIGHTYELLOW_EX +
                          " [SWITCH BOOLEAN]")
                    loopNumber += 1

                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.LIGHTRED_EX + "EXIT" +
                      Fore.LIGHTRED_EX + ": " + " " + Fore.LIGHTYELLOW_EX + " [EXITS TO THE MAIN MENU]")
                print("")
                print(Fore.LIGHTBLUE_EX + "    Type a setting number to do the specific action provided.")
                option = input(":")
                is_number = True
                try:
                    int(option)
                except ValueError:
                    print(Fore.LIGHTRED_EX + "That is not a number!")
                    is_number = False
                    sleep(3.5)
                if is_number:
                    option = int(option)
                    if check_server(serverIP, serverPort) is False:
                        stopped("Lost Connection of the Server!")
                    if option == 1:
                        if not info['info']['YoutubeAccountLogin-in']:
                            reply = youtube_login(serverIP, serverPort)
                            print("")
                            print("")
                            if 'http' in reply:
                                print(Fore.LIGHTRED_EX + "Go to this URL IN YOUR BROWSER: " + reply)
                                print("   "
                                      "On Windows, you should be able to copy the url "
                                      "by selecting the url and right clicking.")
                                sleep(15)
                            else:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                sleep(3.5)
                        else:
                            print("")
                            print("")
                            print("Signing out...")
                            reply = youtube_logout(serverIP, serverPort)
                            if "OK" not in reply:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                sleep(3.5)
                        settings = get_youtube_settings(serverIP, serverPort)
                        info = get_youtube_info(serverIP, serverPort)
                    if option == 2:
                        if check_server(serverIP, serverPort) is False:
                            stopped("Lost Connection of the Server!")
                        print("To Find The Channel_IDs USE THIS: ")
                        print("https://commentpicker.com/youtube-channel-id.php")
                        temp_channel_id = input("Channel ID: ")
                        ok, reply = test_upload(serverIP, serverPort, temp_channel_id)
                        del temp_channel_id
                        print("")
                        print("")
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        else:
                            print(Fore.LIGHTGREEN_EX + "Channel has now been added.")
                        print("")
                        input("Press enter to go back to Selection.")
                        # Refresh
                        if check_server(serverIP, serverPort) is False:
                            stopped("Lost Connection of the Server!")
                        settings = get_youtube_settings(serverIP, serverPort)
                        info = get_youtube_info(serverIP, serverPort)
                    if option > 2:
                        sn = len(settings['settings']) + 2
                        if sn + 1 == option:
                            settings = get_youtube_settings(serverIP, serverPort)
                            info = get_youtube_info(serverIP, serverPort)
                            Screen = "Main"
            elif Screen is "NotificationHold":
                channel_info_last = channel_info
                channel_info = get_channel_info(serverIP, serverPort)
                for channel in channel_info['channels']:
                    channelInfo = channel_info['channel'][channel]
                    channelInfo_last = channel_info_last['channel'][channel]
                    if channelInfo['live'] is True and channelInfo_last['live'] is not True:
                        show_windows_toast_notification("Live Recording Notifications",
                                                        channelInfo['name'] + " is live and is now "
                                                                              "being recorded.")
                sleep(5)
