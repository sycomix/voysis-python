import abc
import six
import uuid
import threading
from datetime import datetime
from dateutil.parser import parse as parsedatetime
from dateutil.tz import tzutc
from voysis.client.user_agent import UserAgent


class ClientError(Exception):
    def __init__(self, *args, **kwargs):
        super(ClientError, self).__init__(*args, **kwargs)
        self.message = args[0] if args and args else None


class ResponseFuture(object):
    def __init__(self,
                 response_code=None,
                 response_message=None,
                 response_entity=None,
                 call_on_complete=None):
        self._event = threading.Event()
        self._callable = call_on_complete
        self._response_entity = None
        self.response_code = response_code
        self.response_message = response_message
        if response_entity:
            self.set(response_entity)

    def wait_until_complete(self, timeout):
        if not self._event.is_set():
            if not self._event.wait(timeout):
                raise ClientError("Timeout waiting on response.")

    def get_entity(self, timeout=None):
        self.wait_until_complete(timeout)
        return self._response_entity

    def set(self, response_code, response_message=None, response_entity=None):
        self._response_entity = response_entity
        self.response_code = response_code
        self.response_message = response_message
        self._event.set()
        if self._callable:
            self._callable(self)

    def is_complete(self):
        return self._event.is_set()


@six.add_metaclass(abc.ABCMeta)
class Client(object):

    def __init__(self, url, user_agent=None):
        self._url = url
        self.user_agent = user_agent if user_agent else UserAgent()
        self.audio_profile_id = str(uuid.uuid4())
        self.api_media_type = 'application/vnd.voysisquery.v1+json'
        self.ignore_vad = False
        self.locale = 'en-US'
        self.check_hostname = True
        self.auth_token = None
        self.current_conversation_id = None
        self.current_context = None
        self._app_token = None
        self._app_token_expiry = datetime.now(tzutc())
        self._audio_type = 'audio/pcm;bits=16;rate=16000'

    @abc.abstractmethod
    def stream_audio(self, frames_generator, notification_handler=None, audio_type=None):
        '''
        Stream audio data to the query API, creating a new conversation (if
        required) and a new audio query. Raises a ClientError if query
        processing is unsuceesful.
        :param frames_generator:
        :param notification_handler A callable that will be invoked if
        streaming to the server is stopped for any reason. The callable
        should accept a single argument, which will be a string indicating
        the reason for the stoppage.
        :param audio_type The Content-Type to use for the audio
        :return: The completed query as a dictionary.
        '''
        pass

    @abc.abstractmethod
    def send_request(self, uri, request_entity=None, extra_headers=None, call_on_complete=None, method='POST'):
        """
        Send a request to the remote server. Raise an exception if the
        request is not successful.
        :param uri: The URI to make the request to.
        :param request_entity: The entity to send in the body of the request.
        :param extra_headers: Any extra headers to include. Every request will
                              have the standard headers set.
        :param call_on_complete: A callable that will be invoked when the response
                                 to the request is completed.
        :param method: The HTTP method to use in sending the request. Defaults to POST.
        :return: A ResponseFuture instance that can be used to obtain the
                 response.
        """
        pass

    def close(self):
        """
        Release any resources in use by this client.
        :return: None
        """
        pass

    def create_common_headers(self):
        headers = {
            'User-Agent': self.user_agent.get(),
            'X-Voysis-Audio-Profile': self.audio_profile_id,
            'X-Voysis-Ignore-Vad': str(self.ignore_vad),
            'Content-Type': 'application/json',
            'Accept': self.api_media_type
        }
        if self._app_token:
            headers['Authorization'] = f'Bearer {self._app_token}'
        return headers

    def send_feedback(self, query_id, rating=None, description=None, durations=None):
        """
        Send feedback to the server for the given query.
        """
        request_body = {}
        if rating:
            request_body['rating'] = rating
        if description:
            request_body['description'] = description
        if durations:
            request_body['durations'] = durations
        if not request_body:
            return None
        uri = "/queries/{query_id}/feedback".format(
            query_id=query_id
        )
        return self.send_request(uri, request_body, method='PATCH').get_entity()

    def refresh_app_token(self, force=False):
        if self.auth_token and (force or self._app_token_expiry < datetime.now(tzutc())):
            auth_headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Accept': 'application/json',
            }
            response_future = self.send_request('/tokens', extra_headers=auth_headers)
            app_token_response = response_future.get_entity(5)
            if response_future.response_code == 200:
                self._app_token = app_token_response['token']
                self._app_token_expiry = parsedatetime(app_token_response['expiresAt'])
        return self._app_token

    def _create_audio_query_entity(self):
        entity = {
            'locale': self.locale,
            'queryType': 'audio',
            'audioQuery': {
                'mimeType': self._audio_type
            }
        }
        if self.current_conversation_id:
            entity['conversationId'] = self.current_conversation_id
        if self.current_context:
            entity['context'] = self.current_context.copy()
        return entity

    def _update_current_context(self, query):
        if 'context' in query:
            self.current_context = query['context'].copy()
        else:
            self.current_context = dict()
