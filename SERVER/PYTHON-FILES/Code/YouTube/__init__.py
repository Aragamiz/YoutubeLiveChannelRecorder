import os
import traceback
from datetime import datetime
from random import randint
from threading import Thread
from time import sleep

from Code.YouTube.utils import get_yt_player_config, get_yt_initial_data, get_endpoint_type, re, get_video_info
from Code.Templates.ChannelObject import TemplateChannel
from Code.utils.web import download_website, download_m3u8_formats
from Code.log import verbose, warning, info, crash_warning
from Code.utils.other import try_get, getTimeZone, get_format_from_data, get_highest_thumbnail, get_utc_offset
from Code.dataHandler import CacheDataHandler
from Code.utils.parser import parse_json
from Code.YouTube.heartbeat import is_live
from Code.utils.windows import show_windows_toast_notification
from Code.encoder import Encoder


class ChannelObject(TemplateChannel):
    platform_name = "YOUTUBE"

    # CHANNEL
    channel_id = None
    channel_name = None

    # SERVER VARIABLES
    recording_status = None
    queue_holder = None

    # WEBSITE Handling
    sharedCookieDict = None

    # YOUTUBE'S HEARTBEAT SYSTEM
    pollDelayMs = 8000
    sequence_number = 0
    broadcast_id = None
    last_heartbeat = None

    # STOP HEARTBEAT
    stop_heartbeat = False

    # USER
    sponsor_on_channel = False

    # VIDEO DETAILS
    video_id = None
    title = None
    description = None
    start_date = None
    privateStream = False
    thumbnail_url = None
    dvr_enabled = False

    thumbnail_location = None
    video_location = None

    # (USED FOR SERVER)
    TestUpload = False

    # Scheduled Live Stream. [HEARTBEAT]
    live_scheduled = False
    live_scheduled_time = None

    # PER-CHANNEL YOUTUBE VARIABLES
    cpn = None

    def __init__(self, channel_id, SettingDict, SharedCookieDict=None, cachedDataHandler=None, queue_holder=None,
                 globalVariables=None):
        """

        :type channel_id: str
        :type cachedDataHandler: CacheDataHandler
        :type SharedCookieDict: dict
        :type globalVariables: GlobalVariables
        """
        self.channel_id = channel_id
        self.cachedDataHandler = cachedDataHandler
        self.sharedCookieDict = SharedCookieDict
        self.cachedDataHandler = cachedDataHandler
        self.globalVariables = globalVariables
        self.DebugMode = SettingDict.get('debug_mode')
        self.EncoderClass = Encoder()
        self.EncoderClass.enable_logs = SettingDict.get('ffmpeg_logs')
        self.queue_holder = queue_holder
        if 'testUpload' in SettingDict:
            self.TestUpload = True

    def loadVideoData(self, video_id=None):
        if video_id is not None:
            websiteClass = download_website("https://www.youtube.com/watch?v={0}".
                                            format(video_id), CookieDict=self.sharedCookieDict)
            self.video_id = video_id
        else:
            websiteClass = download_website("https://www.youtube.com/channel/{0}/live".
                                            format(self.channel_id), CookieDict=self.sharedCookieDict)
        self.sharedCookieDict.update(websiteClass.cookies)
        if websiteClass.text is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if websiteClass.status_code == 404:
            return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                self.channel_id)]
        website_string = websiteClass.text

        endpoint_type = get_endpoint_type(website_string)
        if endpoint_type:
            if endpoint_type == 'browse':
                array = re.findall(r'property="og:title" content="(.+?)"', website_string)
                if array:
                    channel_name = array[0]
                    warning("{0} has the live stream "
                            "currently unlisted or private, or only for members. "
                            "Using safeguard. This may not be the best to leave on.\n".format(channel_name))
                    self.channel_name = channel_name
                    self.video_id = None
                    self.privateStream = True
            else:
                if not endpoint_type == 'watch':
                    warning("Unrecognized endpoint type. Endpoint Type: {0}.".format(endpoint_type))
                verbose("Getting Video ID.")
                yt_player_config = try_get(get_yt_player_config(website_string), lambda x: x, dict)
                player_response = parse_json(try_get(yt_player_config, lambda x: x['args']['player_response'], str))
                videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                if yt_player_config and videoDetails:
                    if "isLiveContent" in videoDetails and \
                            videoDetails['isLiveContent'] and \
                            ("isLive" in videoDetails or "isUpcoming" in videoDetails):
                        self.channel_name = try_get(videoDetails, lambda x: x['author'], str)
                        self.video_id = try_get(videoDetails, lambda x: x['videoId'], str)
                        self.privateStream = False
                        if not self.channel_id:
                            self.channel_id = try_get(videoDetails, lambda x: x['channelId'], str)
                    else:
                        return [False, "Found a stream, the stream seemed to be a non-live stream."]
                else:
                    return [False, "Unable to get yt player config, and videoDetails."]

                if not self.privateStream:
                    # TO AVOID REPEATING REQUESTS.
                    if player_response:
                        # playabilityStatus is legit heartbeat all over again..
                        playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                        status = try_get(playabilityStatus, lambda x: x['status'], str)
                        reason = try_get(playabilityStatus, lambda x: x['reason'], str)
                        if playabilityStatus and status:
                            if 'OK' in status:
                                if reason and 'ended' in reason:
                                    return [False, reason]
                                self.live_streaming = True  # UPDATE SERVER VARIABLE
                                streamingData = try_get(player_response, lambda x: x['streamingData'], dict)
                                if streamingData:
                                    if 'licenseInfos' in streamingData:
                                        licenseInfo = streamingData.get('licenseInfos')
                                        drmFamilies = map(lambda x: x.get('drmFamily'), licenseInfo)
                                        return [False, "This live stream contains DRM and cannot be recorded.\n"
                                                       "DRM Families: {0}".format(', '.join(drmFamilies))]
                                    manifest_url = str(
                                        try_get(streamingData, lambda x: x['hlsManifestUrl'], str))
                                    if not manifest_url:
                                        return [False, "Unable to find HLS Manifest URL."]
                                    formats = download_m3u8_formats(manifest_url)
                                    if formats is None or len(formats) == 0:
                                        return [False, "There were no formats found! Even when the streamer is live."]
                                    f = get_format_from_data(
                                        formats, self.cachedDataHandler.getValue('recordingResolution'))
                                    if not videoDetails:
                                        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                                    thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                                    if thumbnails:
                                        self.thumbnail_url = get_highest_thumbnail(thumbnails)
                                    self.dvr_enabled = try_get(videoDetails, lambda x: x['isLiveDvrEnabled'], bool)
                                    self.StreamInfo = {
                                        'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
                                        'HLSManifestURL': manifest_url,
                                        'DashManifestURL': str(
                                            try_get(player_response, lambda x: x['streamingData']['dashManifestUrl'],
                                                    str)),
                                        'HLSStreamURL': f['url'],
                                    }
                                    self.title = try_get(videoDetails, lambda x: x['title'], str)
                                    self.description = videoDetails['shortDescription']
                                else:
                                    return [False, "No StreamingData, YouTube bugged out!"]
                            if 'live_stream_offline' in status:
                                self.live_streaming = False  # UPDATE SERVER VARIABLE
                    # GET YOUTUBE GLOBAL VARIABLES
                    if self.globalVariables.get("checkedYouTubeVariables") is None:
                        def getSettingsValue(ServiceSettings, settings_nameLook, name=None):
                            for service in ServiceSettings:
                                service_name = try_get(service, lambda x: x['key'], str)
                                if service_name is not None and service_name in settings_nameLook:
                                    value = try_get(service, lambda x: x['value'], str)
                                    if name:
                                        if not value:
                                            warning("Something happened when finding the " + name)
                                            return None
                                    return value
                            return None

                        def getServiceSettings(serviceTrackingParamsList, service_nameLook):
                            if serviceTrackingParamsList:
                                for service in serviceTrackingParamsList:
                                    service_name = try_get(service, lambda x: x['service'], str)
                                    if service_name is not None and service_name in service_nameLook:
                                        return service
                            return None

                        verbose("Getting Global YouTube Variables.")
                        youtube_initial_data = get_yt_initial_data(website_string)
                        e_catcher = getServiceSettings(try_get(youtube_initial_data, lambda x: x['responseContext'][
                            'serviceTrackingParams'], list), "ECATCHER")
                        account_playback_token = try_get(yt_player_config, lambda x: x['args']['account_playback_token'][:-1], str)
                        ps = try_get(yt_player_config, lambda x: x['args']['ps'], str)
                        cbr = try_get(yt_player_config, lambda x: x['args']['cbr'])
                        client_os = try_get(yt_player_config, lambda x: x['args']['cos'])
                        client_os_version = try_get(yt_player_config, lambda x: x['args']['cosver'])
                        if account_playback_token is None:
                            warning("Unable to find account playback token in the YouTube player config.")
                        if ps is None:
                            warning("Unable to find ps in the YouTube player config.")
                        if cbr is None:
                            warning("Unable to find cbr in the YouTube player config.")
                        if client_os is None:
                            warning("Unable to find Client OS in the YouTube player config.")
                        if client_os_version is None:
                            warning("Unable to find Client OS Version in the YouTube player config.")
                        self.globalVariables.set("checkedYouTubeVariables", None)
                        if not youtube_initial_data:
                            warning("Unable to get Youtube Initial Data. Cannot find all Youtube Variables.")
                        elif e_catcher is None:
                            warning("Unable to get ECATCHER service data in Youtube Initial Data. "
                                    "Cannot find all Youtube Variables.")
                        else:
                            params = try_get(e_catcher, lambda x: x['params'], list)
                            page_build_label = getSettingsValue(params, 'innertube.build.label',
                                                                name="Page Build Label")
                            page_cl = getSettingsValue(params, 'innertube.build.changelist', name="Page CL")
                            variants_checksum = getSettingsValue(params, 'innertube.build.variants.checksum',
                                                                 name="Variants Checksum")
                            client_version = getSettingsValue(params, 'client.version', name="Client Version")
                            client_name = getSettingsValue(params, 'client.name', name="Client Name")
                            self.globalVariables.set("page_build_label", page_build_label)
                            self.globalVariables.set("page_cl", page_cl)
                            self.globalVariables.set("client_version", client_version)
                            self.globalVariables.set("client_name", client_name)
                            self.globalVariables.set("variants_checksum", variants_checksum)
                        self.globalVariables.set("ps", ps)
                        self.globalVariables.set("cbr", cbr)
                        self.globalVariables.set("client_os", client_os)
                        self.globalVariables.set("client_os_version", client_os_version)
                        self.globalVariables.set("account_playback_token", account_playback_token)
                        self.globalVariables.set("utf_offset", get_utc_offset())
                        self.globalVariables.set("timezone", getTimeZone())

        # ONLY WORKS IF LOGGED IN
        self.sponsor_on_channel = self.get_sponsor_channel(html_code=website_string)

        self.cpn = self.generate_cpn()
        return [True, "OK"]

    @staticmethod
    def getServiceSettings(serviceTrackingParamsList, service_nameLook):
        if serviceTrackingParamsList:
            for service in serviceTrackingParamsList:
                service_name = try_get(service, lambda x: x['service'], str)
                if service_name is not None and service_name in service_nameLook:
                    return service
        return None

    @staticmethod
    def getSettingsValue(ServiceSettings, settings_nameLook, name=None):
        for service in ServiceSettings:
            service_name = try_get(service, lambda x: x['key'], str)
            if service_name is not None and service_name in settings_nameLook:
                value = try_get(service, lambda x: x['value'], str)
                if name:
                    if not value:
                        warning("Something happened when finding the " + name)
                        return None
                return value
        return None

    @staticmethod
    def generate_cpn():
        """
        Looked at for reference:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1531
        """
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        return ''.join((CPN_ALPHABET[randint(0, 256) & 63] for _ in range(0, 16)))

    def get_sponsor_channel(self, html_code=None):
        # from .. import is_google_account_login_in
        if True:
            verbose("Checking if account sponsored {0}.".format(self.channel_name))
            if html_code is None:
                html_code = download_website("https://www.youtube.com/channel/{0}/live".format(self.channel_id),
                                             CookieDict=self.sharedCookieDict)
                if html_code is None:
                    return None
            html_code = str(html_code)
            array = re.findall('/channel/{0}/membership'.format(self.channel_id), html_code)
            if array:
                return True
            return False
        # return False

    def start_recording(self, enableDVR=False):
        start_index_0 = enableDVR

        if self.StreamInfo is None:
            # Not have gotten already
            if self.isVideoIDinTemp(self.video_id) is False:
                start_index_0 = True  # stream just started for the first time.
            self.recording_status = "Getting Youtube Stream Info."
            self.StreamInfo = get_video_info(
                self, recordingHeight=self.cachedDataHandler.getValue('recordingResolution'))

        if self.StreamInfo:
            self.start_date = datetime.now()
            self.recording_status = "Starting Recording."
            filename = self.create_filename(self.channel_name, self.video_id, self.start_date)
            recordStreams = os.path.join(os.getcwd(), "RecordedStreams")
            if not os.path.exists(recordStreams):
                os.mkdir(recordStreams)
            self.video_location = os.path.join(recordStreams, '{0}.mp4'.format(filename))
            if self.EncoderClass.start_recording(self.StreamInfo['HLSStreamURL'], self.video_location,
                                                 StartIndex0=start_index_0):
                self.recording_status = "Recording."
                show_windows_toast_notification("Live Recording Notifications",
                                                "{0} is live and is now recording. \nRecording at {1}".format(
                                                    self.channel_name, self.StreamInfo['stream_resolution']))
                self.addTemp({
                    'video_id': self.video_id, 'title': self.StreamInfo.get('title'), 'start_date': self.start_date,
                    'file_location': self.video_location, 'channel_name': self.channel_name,
                    'channel_id': self.channel_id, 'description': self.description})
                self.StreamInfo = None
                return True
            else:
                self.recording_status = "Unable to get Youtube Stream Info."
                self.live_streaming = -2
                warning("Unable to get Youtube Stream Info from this stream: ")
                warning("VIDEO ID: {0}".format(str(self.video_id)))
                warning("CHANNEL ID: {0}".format(str(self.channel_id)))
                return False
        return False

    def stop_recording(self):
        while True:
            if self.EncoderClass.last_frame_time:
                last_seconds = (datetime.now() - self.EncoderClass.last_frame_time).total_seconds()
                # IF BACK LIVE AGAIN IN THE MIDDLE OF WAITING FOR NON ACTIVITY.
                if self.live_streaming is True:
                    break
                if last_seconds > 11:
                    self.EncoderClass.stop_recording()
                    self.StreamInfo = None
                    break
            sleep(1)

    def channel_thread(self, enableDVR=False):
        if self.live_streaming is True:
            if self.start_recording(enableDVR=enableDVR):
                if self.TestUpload is True:
                    sleep(10)
                    self.EncoderClass.stop_recording()
                    self.add_youtube_queue()
                    exit(0)

        if self.live_streaming is not None:
            sleep(self.pollDelayMs / 1000)
        try:
            while self.stop_heartbeat is False:
                # LOOP
                self.live_streaming = self.is_live()
                # HEARTBEAT ERROR
                if self.live_streaming == 1:
                    # IF CRASHED.
                    info("Error on Heartbeat on {0}! Trying again ...".format(self.channel_name))
                    sleep(1)
                # INTERNET OFFLiNE.
                elif self.live_streaming is None:
                    warning("INTERNET OFFLINE")
                    sleep(2.4)
                # FALSE
                elif self.live_streaming is False:
                    # TURN OFF RECORDING IF FFMPEG IS STILL ALIVE.
                    if self.EncoderClass.running is True:
                        x = Thread(target=self.stop_recording)
                        x.daemon = True
                        x.start()
                    if self.privateStream is False:
                        info("{0} is not live!".format(self.channel_name))
                        sleep(self.pollDelayMs / 1000)
                    else:
                        info("{0}'s channel live streaming is currently private/unlisted!".format(
                            self.channel_name))
                        sleep(self.pollDelayMs / 1000)
                # LIVE
                elif self.live_streaming is True:
                    # IF FFMPEG IS NOT ALIVE THEN TURN ON RECORDING.
                    if self.EncoderClass.running is not True:
                        x = Thread(target=self.start_recording)
                        x.daemon = True
                        x.start()
                    sleep(self.pollDelayMs / 1000)
                # REPEAT (END OF LOOP)
        except:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))

    def is_live(self, alreadyChecked=False):
        if self.DebugMode is True:
            self.last_heartbeat = datetime.now()
        boolean_live = is_live(self, alreadyChecked=alreadyChecked, CookieDict=self.sharedCookieDict,
                               globalVariables=self.globalVariables)
        return boolean_live

    def close(self):
        if self.EncoderClass:
            self.EncoderClass.stop_recording()
        self.stop_heartbeat = True
