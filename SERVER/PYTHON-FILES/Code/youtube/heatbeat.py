import traceback
from time import sleep

from ..log import warning, YoutubeReply, stopped
from ..utils.other import get_highest_thumbnail, try_get
from ..utils.web import download_json
from ..dataHandler import DownloadThumbnail


def is_live(channel_Class, alreadyChecked=False, cookies=None):
    """

    Checks if channel is live using the normal Youtube heartbeat.
    Also sets heartbeat related variables.

    :type cookies: MozillaCookieJar
    :type channel_Class: ChannelInfo
    :type alreadyChecked: bool
    """

    try:
        try:
            from urllib.parse import urlencode
        except ImportError:
            stopped("Unsupported version of Python. You need Version 3 :<")

        if channel_Class.privateStream is True:
            if alreadyChecked is False:
                ok, message = channel_Class.loadVideoData()
                if not ok:
                    warning(message)
            return False

        from . import account_playback_token, page_build_label, page_cl, variants_checksum, utf_offset, client_version, \
            client_name, timezone
        referer_url = 'https://www.youtube.com/channel/{0}/live'.format(channel_Class.channel_id)
        headers = {'Accept': "*/*", 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'keep-alive', 'dnt': 1,
                   'referer': referer_url, 'x-youtube-client-name': 1}
        url = 'https://www.youtube.com/heartbeat?video_id={0}&heartbeat_token&c={1}&sequence_number={2}'.format(
            channel_Class.video_id, (client_name if client_name is not None else 'WEB'),
            str(channel_Class.sequence_number)
        )
        if account_playback_token is not None:
            headers.update({
                'x-youtube-identity-token': account_playback_token,
            })
        if page_build_label is not None:
            headers.update({
                'x-youtube-page-label': page_build_label,
            })
        if page_cl is not None:
            headers.update({
                'x-youtube-page-cl': page_cl,
            })
        if variants_checksum is not None:
            headers.update({
                'x-youtube-variants-checksum': variants_checksum,
            })
        if utf_offset is not None:
            headers.update({
                'x-youtube-utc-offset': utf_offset,
            })
            url += "&utc_offset_minutes=" + str(utf_offset)
        if client_version is not None:
            headers.update({
                'x-youtube-client-version': client_version,
            })
            url += "&cver=" + client_version
        if timezone is not None:
            url += "&" + urlencode({'time_zone': timezone})

        json = download_json(
            url,
            headers=headers, cookies=cookies)
        if type(json) is bool or json is None:
            return None
        channel_Class.sequence_number += 1
        YoutubeReply('FROM YOUTUBE -> ' + "{}".format(json))

        # SETTING VARIABLES
        liveStreamAbilityRenderer = try_get(json, lambda x: x['liveStreamability']['liveStreamabilityRenderer'], dict)
        if liveStreamAbilityRenderer:
            thumbnail = get_thumbnail(liveStreamAbilityRenderer)
            if thumbnail:
                channel_Class.thumbnail_url = thumbnail
            channel_Class.pollDelayMs = get_poll_delay_ms(liveStreamAbilityRenderer, channel_Class)
            channel_Class.live_scheduled = is_scheduled(liveStreamAbilityRenderer)
            channel_Class.broadcastId = get_broadcast_id(liveStreamAbilityRenderer)

        if channel_Class.live_scheduled is True:
            channel_Class.live_scheduled_time = get_schedule_time(liveStreamAbilityRenderer)
        if 'stop_heartbeat' in json:
            sleep(.5)
            channel_Class.loadVideoData()
            return False
        if 'status' in json:  # Sometimes status is removed and causes an error.
            if "ok" in json['status']:
                return True
            if "stop" in json['status']:
                sleep(.29)
                channel_Class.loadVideoData()
                return False
            if "error" in json['status']:
                warning("Getting the Live Data, failed on Youtube's Side. Youtube Replied with: " + json['reason'])
                return False
            if "live_stream_offline" in json['status']:
                return False
            warning("The Program couldn't find any value that matches the normal heartbeat. Returning False.")
        return False
    except Exception as e1:
        warning("Error occurred when doing Heartbeat/")
        warning("Exception type: " + str(type(e1)) + ", " + str(e1) +
                "\nTraceback: " + traceback.format_exc())
        return 1


# Getting Poll Delay from Heartbeat Json
def get_poll_delay_ms(liveStreamAbilityRenderer, channel_Class):
    pollDelayMs = try_get(liveStreamAbilityRenderer, lambda x: x['pollDelayMs'], str)
    if pollDelayMs:
        return int(pollDelayMs)
    elif channel_Class.pollDelayMs:
        return channel_Class.pollDelayMs
    else:
        return 9500


# Getting Thumbnails from Heartbeat Json
def get_thumbnail(liveStreamAbilityRenderer):
    if DownloadThumbnail() is not True:
        return None
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['liveStreamabilityRenderer']['offlineSlate'], dict)
    thumbnail_list = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer']['thumbnail']['thumbnails'],
                             list)
    if thumbnail_list:
        return get_highest_thumbnail(thumbnail_list)
    return None


# Checking if live stream is scheduled from Heartbeat Json
def is_scheduled(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'], dict)
    if liveStreamOfflineSlateRenderer:
        return 'scheduledStartTime' in liveStreamOfflineSlateRenderer
    return False


def get_schedule_time(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'], dict)
    if liveStreamOfflineSlateRenderer:
        return try_get(liveStreamOfflineSlateRenderer, lambda x: x['subtitleText']['simpleText'], str)
    return None


def get_broadcast_id(liveStreamAbilityRenderer):
    broadcastId = try_get(liveStreamAbilityRenderer, lambda x: x['broadcastId'], str)
    return broadcastId
