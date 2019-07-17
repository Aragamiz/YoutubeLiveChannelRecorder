import argparse
import multiprocessing
from time import sleep
from Code.utils.other import try_get
from Code import run_channel, check_internet, enable_debug, setupStreamsFolder, setupSharedVariables
from Code.log import stopped, warning, disable_youtube_reply, note
from Code.serverHandler import run_server
# from Code.dataHandler import createDataFile, loadData, doesDataExist

if __name__ == '__main__':
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description='Downloads Live streams when Youtube channels are live!')

    # noinspection PyTypeChecker
    parser.add_argument('-p', '--port', type=int, help='Port number', required=False, nargs='+', default=None)
    parser.add_argument('-r', '--disable-reply', action='store_true')
    parser.add_argument('-d', '--enable-debug', action='store_true')

    parser_args = parser.parse_args()

    setupStreamsFolder()
    setupSharedVariables()

    from Code import cached_data_handler
    channel_ids = cached_data_handler.getValue('channel_ids')

    # FOR SSL
    key = try_get(cached_data_handler, lambda x: x.getValue('ssl_key'), str)
    cert = try_get(cached_data_handler, lambda x: x.getValue('ssl_cert'), str)

    note("The delay between checking if channels are live is given by YouTube. The delay may change.")

    if not check_internet():
        stopped("Not able to access the internet!")

    if parser_args.disable_reply:
        disable_youtube_reply()

    if parser_args.enable_debug:
        enable_debug()

    if parser_args.port:
        port = parser_args.port[0]
    else:
        port = 31311

    for channel_id in channel_ids:
        ok, error_message = run_channel(channel_id, startup=True)
        if not ok:
            warning(error_message)
        sleep(.10)

    sleep(.5)

    run_server(port, key=key, cert=cert)

    if len(channel_ids) is 0:
        warning("None channels found added into this program!")
        warning("Connect to localhost on server port using this program's Client, to add channels!")

    del parser_args

    while True:  # Also needed for control+C to work.
        sleep(1)  # Hai! How about you doing? o_O
