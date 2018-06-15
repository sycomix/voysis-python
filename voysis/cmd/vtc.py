import argparse
from collections import defaultdict
from future.builtins import input
import json
import glog as log
import os
import sys
import threading
from time import time
import traceback

from select import select
from voysis import config as config
from voysis.client.client import ClientError
from voysis.client.http_client import HTTPClient
from voysis.client.ws_client import WSClient
from voysis.device.file_device import FileDevice
from voysis.device.mic_device import MicDevice
from voysis.device.mic_array.mic_array import MicArrayDevice
from voysis.version import __version__

MICROPHONE = 'mic'
MICROPHONE_ARRAY = 'mic_ar'
MICROPHONE_DUMMY = 'mic_file'


class RecordingStopper(object):
    """
    A class that can be used to stop a device recording and save interesting event information.
    """
    def __init__(self, device, query_start, durations):
        """
        Create a new RecordingStopper instance.
        :param device: The device that will be stopped.
        :param query_start: The timestamp of the start of the query.
        :param durations: A dict that will be populated with relevant durations.
        """
        self._device = device
        self._query_start = int(query_start * 1000)
        self._durations = durations
        self._mappings = {
            'vad_stop': 'vad',
            'user_stop': 'userStop',
            'query_complete': 'complete'
        }

    def stop_recording(self, reason):
        was_recording = self._device.is_recording()
        self._device.stop_recording()
        if was_recording:
            print("Recording stopped (%s), waiting for response.." % reason)
        if reason:
            event_timestamp = int(time() * 1000) - self._query_start
            duration_name = self._mappings.get(reason, reason)
            self._durations[duration_name] = event_timestamp


def valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return open(arg, 'rb') # return an open file handle


def valid_folder(parser, arg):
    if not os.path.isdir(arg):
        parser.error("The folder %s does not exist!" % arg)
    else:
        return arg


def valid_mic(parser, arg):
    if arg not in [MICROPHONE, MICROPHONE_ARRAY]:
        parser.error('Microphone set to {}. Accepted values: {p1}, {p2}'.format(arg, p1=MICROPHONE, p2=MICROPHONE_ARRAY))
    else:
        return arg


def valid_rating(parser, arg):
    if arg < 1 or arg > 5:
        parser.error('Rating set to {}. Accepted values: 1-5'.format(arg))
    else:
        return arg


def client_factory(url):
    if url.startswith('ws://') or url.startswith('wss://'):
        client = WSClient(url)
        config.apply_config(client, 'client')
        config.apply_config(client, 'ws_client')
    elif url.startswith('http://') or url.startswith('https://'):
        client = HTTPClient(url)
        config.apply_config(client, 'client')
        config.apply_config(client, 'http_client')
    else:
        raise ValueError('No client for protocol in URL %s' % url)
    return client


def device_factory(record, client):
    if record == MICROPHONE_DUMMY:
        device = FileDevice()

    if record == MICROPHONE_ARRAY:
        # TODO make Microphone array stream concatenate all the channels to only one
        raise ValueError('')
        device = None
        # device = MicArrayDevice(client)

    if record == MICROPHONE:
        device = MicDevice(client)

    return device


def stream_mic(client, device, durations):
    print("Ready to capture your voice query")
    input("Press ENTER to start recording")
    query = None
    query_start = time()
    device.start_recording()
    try:
        recording_stopper = RecordingStopper(device, query_start, durations)

        def keyboard_stop():
            print("Press ENTER to stop recording (or wait for VAD)")
            while device.is_recording():
                res = select([sys.stdin], [], [], 1)
                for sel in res[0]:
                    if sel == sys.stdin:
                        recording_stopper.stop_recording('user_stop')

        keyboard_thread = threading.Thread(target=keyboard_stop)
        keyboard_thread.daemon = True
        keyboard_thread.start()
        query = client.stream_audio(device.generate_frames(), notification_handler=recording_stopper.stop_recording, 
                                    audio_type=device.audio_type())
        recording_stopper.stop_recording(None)
    except ValueError:
        pass
    return query


def stream_file(client, device, durations):
    recording_stopper = RecordingStopper(device, time(), durations)
    device.start_recording()
    query = client.stream_audio(device.generate_frames(), notification_handler=recording_stopper.stop_recording, 
                                audio_type=device.audio_type())
    recording_stopper.stop_recording(None)
    return query


def stream(voysis_client, file=None, record=None):
    if file is not None:
        record = MICROPHONE_DUMMY
    device = device_factory(record, voysis_client)
    if isinstance(device, MicDevice) or isinstance(device, MicArrayDevice):
        streamer = stream_mic
    if isinstance(device, FileDevice):
        device.wav_file = file
        streamer = stream_file
    durations = {}
    result = streamer(voysis_client, device, durations)
    print('Durations: ' + (json.dumps(durations)))
    voysis_client.send_feedback(result['id'], durations=durations)
    return result, result['id'], result['conversationId']


def feedback(voysis_client, query_id, rating, description):
    feedback_result = voysis_client.send_feedback(query_id, rating, description)
    return json.dumps(feedback_result, indent=4, sort_keys=True)


def read_context(saved_context_file):
    ctx = defaultdict(lambda: dict(conversationId=None, context=dict()))
    if os.path.isfile(saved_context_file):
        with open(saved_context_file, 'r') as f:
            loaded = json.load(f)
            ctx.update(loaded)
    return ctx


def write_context(context, saved_context_file):
    with open(saved_context_file, 'w') as f:
        json.dump(context, f, indent=4)


def create_parser():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='subcommand', title='subcommands', description='query, feedback')
    parser.add_argument("-u",
                        "--url",
                        dest="url", metavar="str", type=str,
                        help="The URL of the Query API service. Read from config if not specified.")
    parser.add_argument("-c",
                        "--config",
                        default="config.ini", dest="config_file", metavar="str",
                        type=str, help="The name of the config file to use.")
    parser.add_argument("-v",
                        "--version",
                        help="Print the version and exit.",
                        action="version",
                        version=__version__)
    query_parser = subparser.add_parser('query', help='Send audio query and get response.')
    query_parser.add_argument("-c",
                              "--conversation",
                              help="Create a new query in a conversation, using the conversation ID from saved context",
                              default=False,
                              dest="continue_conversation",
                              action='store_true')
    query_parser.add_argument("-x",
                              "--use-context",
                              help="Send saved context along with the query (omit to use a blank context)",
                              default=False,
                              dest="use_context",
                              action='store_true')
    query_parser.add_argument("-s",
                        "--send",
                        dest="wav_fh",
                        help="Send wav file", metavar="FILE",
                        type=lambda x: valid_file(parser, x))
    query_parser.add_argument("-b",
                        "--batch",
                        dest="wav_dir",
                        help="Sends all the wav files from a folder",
                        metavar="DIR",
                        type=lambda x: valid_folder(parser, x))
    query_parser.add_argument("-r",
                        "--record",
                        help="Record from mic and send audio stream. Values: {}, {}, {}".format(MICROPHONE,
                                                                                                MICROPHONE_ARRAY,
                                                                                                MICROPHONE_DUMMY),
                        default="{}".format(MICROPHONE),
                        type=lambda x: valid_mic(parser, x))
    feedback_parser = subparser.add_parser('feedback', help='Send feedback for a particular query.')
    feedback_parser.add_argument("--query-id",
                        dest="query_id",
                        help="Set the query ID for sending feedback. Read from saved context if not provided here.")
    feedback_parser.add_argument("--rating",
                        help="Set the rating (int 1-5) for feedback. Required for feedback request.",
                        type=lambda x: valid_rating(parser, int(x)))
    feedback_parser.add_argument("--description",
                        help="Set a text description to go with the rating in the feedback request. Optional.")

    return parser


def main():
    parser = create_parser()
    try:
        args = parser.parse_args()
        config.load_config(args.config_file)
        saved_context = read_context('context.json')
        url = args.url if args.url else config.get(config.GENERAL, 'url', None)
        voysis_client = client_factory(url)
        if args.subcommand == 'feedback':
            query_id = args.query_id if args.query_id else saved_context[url]['queryId']
            if not query_id:
                print("You must specify the ID of a query to provide feedback for.")
                raise SystemExit(1)
            print("Sending feedback for query ID {}".format(query_id))
            response = feedback(voysis_client, query_id, args.rating, args.description)
            print(response)
        elif args.subcommand == 'query':
            if args.continue_conversation:
                voysis_client.current_conversation_id = saved_context[url]['conversationId']
            if args.use_context:
                voysis_client.current_context = saved_context[url]['context'].copy()
            if not args.wav_dir:
                response, query_id, conversation_id = stream(voysis_client, args.wav_fh, args.record)
                json.dump(response, sys.stdout, indent=4)
                saved_context[url]['conversationId'] = conversation_id
                saved_context[url]['queryId'] = query_id
                saved_context[url]['context'] = voysis_client.current_context
                write_context(saved_context, 'context.json')
            else:
                for root, dirs, files in os.walk(args.wav_dir):
                    log.info('Streaming files from folder {} over {}'.format(args.wav_dir, args.api_flavour))
                    for file in files:
                        if file.endswith('.wav'):
                            file_path = os.path.join(args.wav_dir, file)
                            log.info('Streaming {}'.format(file_path))
                            response, query_id, conversation_id = stream(voysis_client, open(file_path, 'rb'))
                            json.dump(response, sys.stdout, indent=4)
        else:
            raise ValueError('Unsupported subcommand.')
        voysis_client.close()
    except ClientError as client_error:
        log.error(client_error.message)
    except Exception as e:
        log.info(traceback.format_exc())
        log.info('Error: {err}'.format(err=e))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("DONE")
